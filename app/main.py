"""Aplicación académica ES3: portal ciudadano + gestión de funcionarios.

Inicio local: uvicorn app.main:app --reload
No utilizar con datos reales de pacientes sin una evaluación formal de seguridad y privacidad.
"""
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
import hashlib
from pathlib import Path
from threading import Lock
from time import monotonic
import os
import re
import secrets
from urllib.parse import quote
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session
from jinja2 import Environment
from fastapi.templating import Jinja2Templates

from .database import get_db, init_database, catalog, INSTANCE, SessionLocal
from .models import (Unit, Role, Staff, Case, CaseEvent, Survey, SurveyQuestion,
                     RecordType, Channel, Category, CaseStatus, Citizen, Attachment, Audit)
from .security import APP_SECRET, ROLES, hash_password, verify_password, new_folio, new_tracking_code, tracking_hash, check_tracking, csrf_for, verify_csrf, can_view_case, can_edit_case, can_reassign, valid_new_password, PASSWORD_POLICY_MESSAGE

BASE = Path(__file__).resolve().parent
PRIVATE_DIR = INSTANCE / 'private_uploads'
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024

@asynccontextmanager
async def lifespan(app):
    init_database()
    yield

app = FastAPI(title='Salud PLC - Evaluación Sumativa 3', docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET, session_cookie='salud_plc_session', max_age=7200, same_site='lax', https_only=os.getenv('COOKIE_SECURE', '0') == '1')
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
templates.env.globals['roles'] = ROLES


@app.middleware('http')
async def protect_private_history(request: Request, call_next):
    """Evitar el caché privado y reducir exposición a ataques del navegador."""
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:"
    )
    if os.getenv('COOKIE_SECURE', '0') == '1' and request.url.scheme == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    route = request.url.path
    if route.startswith('/funcionarios') or route in ('/solicitud', '/seguimiento'):
        response.headers['Cache-Control'] = 'private, no-store, no-cache, max-age=0, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

FACILITIES = ['CESFAM Padre Las Casas', 'CESFAM Las Colinas', 'CESFAM Pulmahue', 'CESFAM Conunhuenu', 'SAR Padre Las Casas', 'Centro Comunitario de Rehabilitación (CCR)', 'Otro establecimiento / no sé']
STATES = ['Recibido', 'En proceso', 'Derivado', 'Cerrado']
TYPES = ['Reclamo', 'Sugerencia', 'Agradecimiento']

_attempts: dict[tuple, list[float]] = defaultdict(list)
_attempt_lock = Lock()

def limit_rate(request: Request, action: str, max_calls: int, window: int):
    """Límite básico de desarrollo por IP. Para producción reemplazar con almacén compartido."""
    ip = request.client.host if request.client else 'unknown'
    now = monotonic()
    key = (action, ip)
    with _attempt_lock:
        recent = [t for t in _attempts[key] if now - t < window]
        if len(recent) >= max_calls:
            raise HTTPException(429, 'Demasiados intentos. Intenta más tarde.')
        recent.append(now)
        _attempts[key] = recent

def context(request: Request, db: Session, **extras):
    user = current_user(request, db)
    notice = db.scalar(select(Audit).where(Audit.event_type == 'public_notice').order_by(Audit.id.desc()).limit(1))
    if notice:
        notice = SimpleNamespace(text=notice.details.get('text', ''))
    categories = list(db.scalars(select(Category.name).where(Category.active.is_(True)).order_by(Category.name)))
    all_categories = list(db.scalars(select(Category.name).order_by(Category.name)))
    return dict(request=request, csrf_token=csrf_for(request), current_user=user, notice=notice,
                facilities=FACILITIES, categories=categories, all_categories=all_categories,
                states=STATES, types=TYPES, **extras)


def active_category_names(db: Session):
    return list(db.scalars(select(Category.name).where(Category.active.is_(True))))


def category_names(db: Session):
    return list(db.scalars(select(Category.name)))

def render(request, db, template, status_code=200, **extras):
    return templates.TemplateResponse(request=request, name=template, context=context(request, db, **extras), status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def page_http_error(request: Request, exc: StarletteHTTPException):
    """Los errores de navegación y formularios no deben abrir respuestas JSON crudas."""
    if 300 <= exc.status_code < 400 and exc.headers and exc.headers.get('Location'):
        return RedirectResponse(exc.headers['Location'], status_code=exc.status_code)

    with SessionLocal() as db:
        # Mantener a la persona en el formulario cuando falla una regla del servidor.
        pages = {'/solicitud': 'solicitud.html', '/encuesta': 'encuesta.html',
                 '/seguimiento': 'seguimiento.html', '/funcionarios/login': 'login.html'}
        if request.method == 'POST' and exc.status_code in (400, 413):
            form = await request.form()
            values = {
                key: val[:500] for key, val in form.items()
                if isinstance(val, str) and key not in ('csrf_token', 'password', 'tracking_code')
            }
            path = request.url.path
            if path in pages:
                return render(request, db, pages[path], status_code=exc.status_code,
                              error=str(exc.detail), values=values,
                              selected_type=values.get('case_type', 'Reclamo'))
            user = current_user(request, db)
            if user and user.role == 'admin' and path == '/funcionarios/unidades':
                return render(request, db, 'unidades.html', status_code=exc.status_code,
                              error=str(exc.detail), values=values,
                              units=list(db.scalars(select(Unit).order_by(Unit.name))))
            if user and user.role == 'admin' and path.startswith('/funcionarios/categorias'):
                return render(request, db, 'categorias.html', status_code=exc.status_code,
                              error=str(exc.detail), values=values,
                              category_rows=list(db.scalars(select(Category).order_by(Category.name))))
            if user and user.role == 'admin' and path == '/funcionarios/equipo':
                return render(request, db, 'equipo.html', status_code=exc.status_code,
                              error=str(exc.detail), values=values,
                              users=list(db.scalars(select(Staff).order_by(Staff.id))),
                              units=list(db.scalars(select(Unit).where(Unit.active == True))))
            if user and user.role in ('admin', 'contenidos') and path == '/funcionarios/avisos':
                return render(request, db, 'avisos.html', status_code=exc.status_code,
                              error=str(exc.detail), text=values.get('text', ''))
            case_match = re.fullmatch(r'/funcionarios/casos/(\d+)/actualizar', path)
            if user and case_match:
                case = db.get(Case, int(case_match.group(1)))
                if case and can_edit_case(user, case):
                    return render(request, db, 'caso_detalle.html', status_code=exc.status_code,
                                  error=str(exc.detail), values=values, user=user, case=case,
                                  units=list(db.scalars(select(Unit).where(Unit.active == True).order_by(Unit.name))),
                                  can_edit=True, can_assign=can_reassign(user))
        return render(request, db, 'error.html', status_code=exc.status_code,
                      error_status=exc.status_code, error_message=str(exc.detail))


@app.exception_handler(RequestValidationError)
async def page_validation_error(request: Request, exc: RequestValidationError):
    # P. ej., una URL con un identificador que no es un número válido.
    with SessionLocal() as db:
        return render(request, db, 'error.html', status_code=422, error_status=422,
                      error_message='Los datos de la solicitud no son válidos. Revisa la información e inténtalo nuevamente.')

def current_user(request: Request, db: Session):
    uid = request.session.get('staff_id')
    login_id = request.session.get('login_audit_id')
    nonce = request.session.get('session_nonce')
    last_seen = request.session.get('last_seen')
    if not isinstance(uid, int):
        return None
    now = datetime.now(timezone.utc).timestamp()
    if (not isinstance(login_id, int) or not isinstance(nonce, str) or
            not isinstance(last_seen, (int, float)) or
            now - last_seen > 1800 or last_seen > now + 60):
        request.session.clear()
        return None
    staff = db.get(Staff, uid)
    session_audit = db.get(Audit, login_id)
    hashed_nonce = hashlib.sha256(nonce.encode()).hexdigest()
    if (not staff or not staff.active or not session_audit or
            session_audit.actor_id != uid or session_audit.event_type != 'inicio_sesion' or
            not secrets.compare_digest(session_audit.details.get('sid_hash', ''), hashed_nonce)):
        request.session.clear()
        return None
    revoked = db.scalar(select(Audit.id).where(
        Audit.actor_id == uid,
        Audit.event_type == 'cierre_sesion',
        Audit.details['sid_hash'].as_string() == hashed_nonce,
    ).limit(1))
    if revoked:
        request.session.clear()
        return None
    request.session['last_seen'] = now
    return staff

def user_required(request: Request, db: Session):
    user = current_user(request, db)
    if not user:
        raise HTTPException(303, headers={'Location': '/funcionarios/login?sesion=finalizada'})
    return user

def permitted_cases_query(staff):
    q = (select(Case)
         .where(Case.record_type.has(RecordType.name != 'Encuesta'))
         .order_by(Case.created_at.desc(), Case.id.desc()))
    if staff.role not in ('admin', 'jefatura'):
        q = q.where(Case.unit_id == staff.unit_id)
    return q

def validate_one(value: str, options: list[str], name: str):
    if value not in options:
        raise HTTPException(400, f'{name} inválido')
    return value

def form_str(form, key, max_len=300):
    val = form.get(key, '')
    if not isinstance(val, str):
        raise HTTPException(400, 'Campo inválido')
    val = val.strip()
    if len(val) > max_len:
        raise HTTPException(400, f'El campo {key} supera el máximo permitido')
    return val

@app.get('/', response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, db, 'home.html')

@app.get('/solicitud', response_class=HTMLResponse)
def new_case_page(request: Request, tipo: str = '', db: Session = Depends(get_db)):
    return render(request, db, 'solicitud.html', selected_type=tipo if tipo in TYPES else 'Reclamo')

@app.post('/solicitud', response_class=HTMLResponse)
async def create_case(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    limit_rate(request, 'case_submit', 10, 600)
    case_type = validate_one(form_str(form, 'case_type'), TYPES, 'Tipo de solicitud')
    facility = validate_one(form_str(form, 'facility'), FACILITIES, 'Establecimiento')
    category = validate_one(form_str(form, 'category'), active_category_names(db), 'Categoría')
    source_area = form_str(form, 'source_area', 100) or 'Sin especificar'
    description = form_str(form, 'description', 500)
    if len(description) < 15:
        raise HTTPException(400, 'Describe tu experiencia con al menos 15 caracteres.')
    contact_name = form_str(form, 'contact_name', 100)
    contact_email = form_str(form, 'contact_email', 255)
    contact_consent = form.get('contact_consent') == 'on'
    if contact_name or contact_email:
        if not contact_consent or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', contact_email):
            raise HTTPException(400, 'Para dejar un contacto voluntario debes aceptar el consentimiento e ingresar un correo válido.')
    uploaded = form.get('attachment')
    data = None
    media_type = None
    extension = None
    original_filename = None
    if uploaded is not None and getattr(uploaded, 'filename', ''):
        data = await uploaded.read(MAX_ATTACHMENT_BYTES + 1)
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(413, 'El archivo supera el máximo de 2 MB.')
        if data.startswith(b'%PDF-'):
            media_type, extension = 'application/pdf', '.pdf'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            media_type, extension = 'image/png', '.png'
        elif data.startswith(b'\xff\xd8\xff'):
            media_type, extension = 'image/jpeg', '.jpg'
        else:
            raise HTTPException(400, 'Adjunta únicamente PDF, PNG o JPG válidos.')
        original_filename = uploaded.filename.replace('\\', '/').split('/')[-1][:255]
        if not original_filename:
            original_filename = f'adjunto{extension}'
    unit = db.scalar(select(Unit).where(Unit.name == 'Mesa de entrada'))
    if not unit:
        raise HTTPException(503, 'No existe una unidad receptora configurada')
    folio = new_folio()
    token = new_tracking_code()
    citizen = None
    if contact_name or contact_email:
        citizen = Citizen(alias=contact_name or None, email=contact_email, contact_consent=True)
        db.add(citizen)
        db.flush()
    case = Case(
        folio=folio, tracking_hmac=tracking_hash(token),
        record_type_id=catalog(db, RecordType, 'name', case_type).id,
        channel_id=catalog(db, Channel, 'name', 'Portal web').id,
        category_id=catalog(db, Category, 'name', category).id,
        status_id=catalog(db, CaseStatus, 'name', 'Recibido').id,
        facility=facility, source_area=source_area, description=description,
        citizen_id=citizen.id if citizen else None,
        unit_id=unit.id,
    )
    case.events.append(CaseEvent(action='Registro recibido', note='Ingresado mediante portal ciudadano',
                                 status_id=case.status_id, target_unit_id=unit.id))
    db.add(case)
    db.flush()
    db.add(Audit(record_id=case.id, event_type='registro_creado', details={'tipo': case_type, 'origen': 'Portal web'}))
    file_path = None
    try:
        if data is not None:
            PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
            storage_key = secrets.token_hex(24) + extension
            file_path = PRIVATE_DIR / storage_key
            with file_path.open('xb') as target:
                target.write(data)
            db.add(Attachment(record_id=case.id, original_filename=original_filename,
                              storage_key=storage_key, mime_type=media_type, size_bytes=len(data)))
        db.commit()
    except Exception:
        db.rollback()
        if file_path is not None:
            file_path.unlink(missing_ok=True)
        raise
    return render(request, db, 'comprobante.html', folio=folio, tracking_code=token)

@app.get('/encuesta', response_class=HTMLResponse)
def survey_page(request: Request, db: Session = Depends(get_db)):
    return render(request, db, 'encuesta.html')

@app.post('/encuesta', response_class=HTMLResponse)
async def submit_survey(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    limit_rate(request, 'survey', 15, 600)
    rating_str = form_str(form, 'rating', 1)
    if rating_str not in ('1', '2', '3', '4', '5'):
        raise HTTPException(400, 'La calificación debe estar entre 1 y 5')
    facility = validate_one(form_str(form, 'facility'), FACILITIES, 'Establecimiento')
    aspect = validate_one(form_str(form, 'aspect'), active_category_names(db), 'Aspecto')
    record = Case(
        folio=new_folio(), tracking_hmac=tracking_hash(new_tracking_code()),
        record_type_id=catalog(db, RecordType, 'name', 'Encuesta').id,
        channel_id=catalog(db, Channel, 'name', 'Portal web').id,
        category_id=catalog(db, Category, 'name', aspect).id,
        facility=facility, source_area='Encuesta anónima',
    )
    db.add(record)
    db.flush()
    question = catalog(db, SurveyQuestion, 'code', 'SAT_GENERAL')
    db.add(Survey(record_id=record.id, question_id=question.id, rating=int(rating_str)))
    db.add(Audit(record_id=record.id, event_type='encuesta_creada', details={'anonima': True}))
    db.commit()
    return render(request, db, 'encuesta_gracias.html')

@app.get('/seguimiento', response_class=HTMLResponse)
def lookup_page(request: Request, db: Session = Depends(get_db)):
    return render(request, db, 'seguimiento.html')

@app.post('/seguimiento', response_class=HTMLResponse)
async def lookup(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    limit_rate(request, 'lookup', 12, 600)
    folio = form_str(form, 'folio', 40).upper()
    secret_code = form_str(form, 'tracking_code', 100)
    case = db.scalar(select(Case).where(Case.folio == folio))
    if not case or not check_tracking(case.tracking_hmac, secret_code):
        return render(request, db, 'seguimiento.html', error='No encontramos una solicitud con ese folio y código privado.')
    # No mostrar descripción, nombre de funcionario, notas internas ni unidad interna.
    return render(request, db, 'seguimiento.html', result=dict(folio=case.folio, status=case.status, created=case.created_at, updated=case.updated_at))

@app.get('/funcionarios/login', response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if current_user(request, db):
        return RedirectResponse('/funcionarios/panel', status_code=303)
    session_notice = None
    if request.query_params.get('sesion'):
        session_notice = 'No puedes ingresar a Gestión porque tu sesión está cerrada. Vuelve a iniciar sesión.'
    elif request.query_params.get('cerrada'):
        session_notice = 'Cerraste sesión correctamente. Para volver a Gestión debes iniciar sesión nuevamente.'
    return render(request, db, 'login.html', session_notice=session_notice)


@app.get('/funcionarios/sesion-actual', include_in_schema=False)
def session_status(request: Request, db: Session = Depends(get_db)):
    """Comprobación sin datos personales para el historial atrás/adelante."""
    return Response(status_code=204 if current_user(request, db) else 401)

@app.post('/funcionarios/login')
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    limit_rate(request, 'login', 6, 300)
    email = form_str(form, 'email', 255).lower()
    pwd = form_str(form, 'password', 200)
    user = db.scalar(select(Staff).where(Staff.email == email))
    if not user or not user.active or not verify_password(user.password_hash, pwd):
        db.add(Audit(actor_id=user.id if user else None, event_type='inicio_sesion_fallido',
                     details={'resultado': 'denegado'}))
        db.commit()
        return render(request, db, 'login.html', status_code=401, error='Correo o contraseña incorrectos.')
    session_nonce = secrets.token_urlsafe(32)
    audit = Audit(actor_id=user.id, event_type='inicio_sesion',
                  details={'resultado': 'correcto', 'sid_hash': hashlib.sha256(session_nonce.encode()).hexdigest()})
    db.add(audit)
    db.commit()
    request.session.clear()
    request.session['staff_id'] = user.id
    request.session['login_audit_id'] = audit.id
    request.session['session_nonce'] = session_nonce
    request.session['last_seen'] = datetime.now(timezone.utc).timestamp()
    csrf_for(request)
    return RedirectResponse('/funcionarios/panel', status_code=303)

@app.post('/funcionarios/salir')
async def logout(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = current_user(request, db)
    if user:
        session_nonce = request.session.get('session_nonce', '')
        db.add(Audit(actor_id=user.id, event_type='cierre_sesion',
                     details={'sid_hash': hashlib.sha256(session_nonce.encode()).hexdigest()}))
        db.commit()
    request.session.clear()
    return RedirectResponse('/funcionarios/login?cerrada=1', status_code=303)

@app.get('/funcionarios/panel', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role == 'contenidos':
        return RedirectResponse('/funcionarios/avisos', status_code=303)
    # El alcance por unidad se aplica antes de cualquier filtro o paginación.
    visible = permitted_cases_query(user)
    total_cases = list(db.scalars(visible))
    totals = {'total': len(total_cases), 'open': sum(c.status != 'Cerrado' for c in total_cases), 'closed': sum(c.status == 'Cerrado' for c in total_cases)}
    filters = {key: request.query_params.get(key, '').strip() for key in ('q', 'status', 'case_type', 'category', 'facility')}
    if len(filters['q']) > 80:
        raise HTTPException(400, 'La búsqueda es demasiado larga')
    for key, choices in [('status', STATES), ('case_type', TYPES), ('category', category_names(db)), ('facility', FACILITIES)]:
        if filters[key] and filters[key] not in choices:
            raise HTTPException(400, 'Filtro inválido')
    query = visible
    if filters['q']:
        # La marca ! funciona como escape tanto en PostgreSQL como en SQLite.
        escaped = filters['q'].replace('!', '!!').replace('%', '!%').replace('_', '!_')
        pattern = f'%{escaped}%'
        query = query.where(or_(Case.folio.ilike(pattern, escape='!'), Case.description.ilike(pattern, escape='!')))
    if filters['status']:
        query = query.where(Case.status_record.has(CaseStatus.name == filters['status']))
    if filters['case_type']:
        query = query.where(Case.record_type.has(RecordType.name == filters['case_type']))
    if filters['category']:
        query = query.where(Case.category_record.has(Category.name == filters['category']))
    if filters['facility']:
        query = query.where(Case.facility == filters['facility'])
    try:
        page = int(request.query_params.get('page', '1'))
    except ValueError:
        raise HTTPException(400, 'Página inválida')
    if page < 1 or page > 100000:
        raise HTTPException(400, 'Página inválida')
    filtered_count = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    page_count = max(1, (filtered_count + 19) // 20)
    if page > page_count:
        raise HTTPException(404, 'No existen resultados para esa página')
    cases = list(db.scalars(query.limit(20).offset((page-1)*20)))
    return render(request, db, 'panel.html', user=user, cases=cases, totals=totals,
                  filters=filters, filtered_count=filtered_count, page=page, page_count=page_count)

@app.get('/funcionarios/casos/{case_id}', response_class=HTMLResponse)
def case_detail(case_id: int, request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    case = db.get(Case, case_id)
    if not case or not can_view_case(user, case):
        raise HTTPException(404, 'Caso no disponible')
    units = list(db.scalars(select(Unit).where(Unit.active == True).order_by(Unit.name)))
    return render(request, db, 'caso_detalle.html', user=user, case=case, units=units, can_edit=can_edit_case(user, case), can_assign=can_reassign(user))


@app.get('/funcionarios/adjuntos/{attachment_id}')
def download_attachment(attachment_id: int, request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    attachment = db.get(Attachment, attachment_id)
    if not attachment or not can_view_case(user, attachment.record):
        raise HTTPException(404, 'Adjunto no disponible')
    path = PRIVATE_DIR / attachment.storage_key
    if not path.is_file():
        raise HTTPException(404, 'Archivo no encontrado')
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.original_filename,
                        content_disposition_type='attachment')

@app.post('/funcionarios/casos/{case_id}/actualizar')
async def update_case(case_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    case = db.get(Case, case_id)
    if not case or not can_edit_case(user, case):
        raise HTTPException(403, 'No tienes autorización para modificar el caso')
    status = validate_one(form_str(form, 'status'), STATES, 'Estado')
    category = form_str(form, 'category') or case.category
    if category != case.category:
        validate_one(category, active_category_names(db), 'Categoría')
    note = form_str(form, 'note', 500)
    unit_id = case.unit_id
    if can_reassign(user):
        selected_unit = form_str(form, 'unit_id', 10)
        try:
            if selected_unit:
                unit_id = int(selected_unit)
        except ValueError:
            raise HTTPException(400, 'Unidad inválida')
        unit = db.get(Unit, unit_id)
        if not unit or not unit.active:
            raise HTTPException(400, 'Unidad no disponible')
    if status == case.status and unit_id == case.unit_id and category == case.category and not note:
        return RedirectResponse(f'/funcionarios/casos/{case.id}', status_code=303)
    action = f'Estado {case.status} → {status}' if status != case.status else 'Seguimiento registrado'
    if unit_id != case.unit_id: action += ' · Derivación de unidad'
    if category != case.category: action += f' · Clasificación {case.category} → {category}'
    case.status_id = catalog(db, CaseStatus, 'name', status).id
    case.unit_id = unit_id
    case.category_id = catalog(db, Category, 'name', category).id
    case.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(CaseEvent(case_id=case.id, actor_id=user.id, status_id=case.status_id,
                     target_unit_id=unit_id, action=action, note=note))
    db.add(Audit(record_id=case.id, actor_id=user.id, event_type='seguimiento_actualizado',
                 details={'estado': status, 'categoria': category, 'unidad_id': unit_id}))
    db.commit()
    # Si recepción deriva a otra unidad, pierde acceso al caso de forma inmediata.
    destino = f'/funcionarios/casos/{case.id}?guardado=1' if can_view_case(user, case) else '/funcionarios/panel'
    return RedirectResponse(destino, status_code=303)

@app.get('/funcionarios/reportes', response_class=HTMLResponse)
def reports(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role == 'contenidos': raise HTTPException(403, 'Acceso denegado')
    filters = {key: request.query_params.get(key, '').strip() for key in ('desde', 'hasta', 'category', 'case_type')}
    if filters['category'] and filters['category'] not in category_names(db):
        raise HTTPException(400, 'La categoría del reporte no es válida.')
    if filters['case_type'] and filters['case_type'] not in TYPES:
        raise HTTPException(400, 'El tipo de solicitud del reporte no es válido.')
    bounds = {}
    for field in ('desde', 'hasta'):
        value = filters[field]
        if value:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise HTTPException(400, 'La fecha debe tener el formato AAAA-MM-DD.')
            try:
                bounds[field] = date.fromisoformat(value)
            except ValueError:
                raise HTTPException(400, 'La fecha ingresada no existe.')
    if bounds.get('desde') and bounds.get('hasta') and bounds['desde'] > bounds['hasta']:
        raise HTTPException(400, 'La fecha inicial no puede ser posterior a la fecha final.')

    query = permitted_cases_query(user)
    if 'desde' in bounds:
        query = query.where(Case.created_at >= datetime.combine(bounds['desde'], time.min))
    if 'hasta' in bounds:
        query = query.where(Case.created_at <= datetime.combine(bounds['hasta'], time.max))
    if filters['category']:
        query = query.where(Case.category_record.has(Category.name == filters['category']))
    if filters['case_type']:
        query = query.where(Case.record_type.has(RecordType.name == filters['case_type']))
    cases = list(db.scalars(query))
    by_type = [(name, sum(c.case_type == name for c in cases)) for name in TYPES]
    by_status = [(name, sum(c.status == name for c in cases)) for name in STATES]
    by_category = [(name, sum(c.category == name for c in cases)) for name in category_names(db)]
    by_facility = [(name, sum(c.facility == name for c in cases)) for name in FACILITIES if any(c.facility == name for c in cases)]
    rating_query = select(Survey.rating).join(Survey.record)
    if 'desde' in bounds:
        rating_query = rating_query.where(Case.created_at >= datetime.combine(bounds['desde'], time.min))
    if 'hasta' in bounds:
        rating_query = rating_query.where(Case.created_at <= datetime.combine(bounds['hasta'], time.max))
    if filters['category']:
        rating_query = rating_query.where(Case.category_record.has(Category.name == filters['category']))
    ratings = list(db.scalars(rating_query)) if user.role in ('admin', 'jefatura') and not filters['case_type'] else []
    avg = round(sum(ratings)/len(ratings), 1) if ratings else None
    by_rating = [(score, ratings.count(score)) for score in range(1,6)]
    return render(request, db, 'reportes.html', user=user, by_type=by_type, by_status=by_status,
                  by_category=by_category, by_facility=by_facility, by_rating=by_rating,
                  avg=avg, survey_count=len(ratings), filters=filters, report_total=len(cases))


@app.get('/funcionarios/categorias', response_class=HTMLResponse)
def categories_page(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role != 'admin':
        raise HTTPException(403, 'Solo administración puede configurar categorías.')
    return render(request, db, 'categorias.html',
                  category_rows=list(db.scalars(select(Category).order_by(Category.name))))


@app.post('/funcionarios/categorias')
async def add_category(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role != 'admin':
        raise HTTPException(403, 'Solo administración puede configurar categorías.')
    name = form_str(form, 'name', 70)
    if len(name) < 3 or not re.fullmatch(r'[\w\s/-]+', name, flags=re.UNICODE):
        raise HTTPException(400, 'El nombre debe tener entre 3 y 70 caracteres y no contener símbolos especiales.')
    if db.scalar(select(Category.id).where(func.lower(Category.name) == name.lower())):
        raise HTTPException(400, 'Esa categoría ya existe. Puedes habilitarla si está desactivada.')
    db.add(Category(name=name, active=True))
    db.add(Audit(actor_id=user.id, event_type='categoria_creada', details={'nombre': name}))
    db.commit()
    return RedirectResponse('/funcionarios/categorias?guardado=1', status_code=303)


@app.post('/funcionarios/categorias/{category_id}/estado')
async def toggle_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role != 'admin':
        raise HTTPException(403, 'Solo administración puede configurar categorías.')
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(404, 'Categoría no encontrada.')
    if category.name == 'Otro' and category.active:
        raise HTTPException(400, 'La categoría Otro debe permanecer disponible para casos no clasificados.')
    category.active = not category.active
    db.add(Audit(actor_id=user.id, event_type='categoria_estado',
                 details={'nombre': category.name, 'activa': category.active}))
    db.commit()
    return RedirectResponse('/funcionarios/categorias?guardado=1', status_code=303)

@app.get('/funcionarios/unidades', response_class=HTMLResponse)
def units_page(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role != 'admin': raise HTTPException(403, 'Solo administración')
    units = list(db.scalars(select(Unit).order_by(Unit.name)))
    return render(request, db, 'unidades.html', units=units)

@app.post('/funcionarios/unidades')
async def add_unit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role != 'admin': raise HTTPException(403, 'Solo administración')
    name = form_str(form, 'name', 100)
    desc = form_str(form, 'description', 300)
    if len(name) < 3 or db.scalar(select(Unit).where(func.lower(Unit.name) == name.lower())):
        return render(request, db, 'unidades.html', status_code=400, units=list(db.scalars(select(Unit))),
                      values={'name': name, 'description': desc}, error='Nombre inválido o ya existente.')
    db.add(Unit(name=name, description=desc))
    db.commit()
    return RedirectResponse('/funcionarios/unidades', status_code=303)

@app.get('/funcionarios/equipo', response_class=HTMLResponse)
def team_page(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role != 'admin': raise HTTPException(403, 'Solo administración')
    users = list(db.scalars(select(Staff).order_by(Staff.id)))
    units = list(db.scalars(select(Unit).where(Unit.active == True)))
    return render(request, db, 'equipo.html', users=users, units=units)

@app.post('/funcionarios/equipo')
async def add_staff(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role != 'admin': raise HTTPException(403, 'Solo administración')
    name = form_str(form, 'name', 120)
    email = form_str(form, 'email', 255).lower()
    pwd = form_str(form, 'password', 200)
    role = form_str(form, 'role', 30)
    try: unit_id = int(form_str(form, 'unit_id', 10))
    except ValueError: raise HTTPException(400, 'Unidad inválida')
    password_valid = valid_new_password(pwd)
    if (len(name) < 3 or '@' not in email or not password_valid or role not in ROLES or not db.get(Unit, unit_id) or db.scalar(select(Staff).where(Staff.email == email))):
        error = PASSWORD_POLICY_MESSAGE if not password_valid else 'Revisa los datos: correo único, nombre, rol y unidad válidos.'
        return render(request, db, 'equipo.html', status_code=400, error=error,
                      values={'name': name, 'email': email, 'role': role, 'unit_id': str(unit_id)},
                      users=list(db.scalars(select(Staff))), units=list(db.scalars(select(Unit))))
    role_row = catalog(db, Role, 'code', role)
    db.add(Staff(full_name=name, email=email, password_hash=hash_password(pwd),
                 role_id=role_row.id, unit_id=unit_id, active=True))
    db.commit()
    return RedirectResponse('/funcionarios/equipo', status_code=303)

@app.get('/funcionarios/avisos', response_class=HTMLResponse)
def notices_page(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role not in ('admin', 'contenidos'): raise HTTPException(403, 'Acceso restringido')
    notice = db.scalar(select(Audit).where(Audit.event_type == 'public_notice').order_by(Audit.id.desc()).limit(1))
    return render(request, db, 'avisos.html', text=notice.details.get('text', '') if notice else '')

@app.post('/funcionarios/avisos')
async def update_notice(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role not in ('admin', 'contenidos'): raise HTTPException(403, 'Acceso restringido')
    text = form_str(form, 'text', 500)
    db.add(Audit(event_type='public_notice', actor_id=user.id, details={'text': text}))
    db.commit()
    return RedirectResponse('/funcionarios/avisos?guardado=1', status_code=303)
