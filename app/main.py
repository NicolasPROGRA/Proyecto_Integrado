"""Versión 0.1 de aplicación web integrada: portal público + panel de funcionarios.

Inicio local: uvicorn app.main:app --reload
No utilizar con datos reales de pacientes sin una evaluación formal de seguridad y privacidad.
"""
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
import os
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from jinja2 import Environment
from fastapi.templating import Jinja2Templates

from .database import get_db, init_database
from .models import Unit, Staff, Case, CaseEvent, Survey, Notice
from .security import APP_SECRET, ROLES, hash_password, verify_password, new_folio, new_tracking_code, tracking_hash, check_tracking, csrf_for, verify_csrf, can_view_case, can_edit_case, can_reassign

BASE = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app):
    init_database()
    yield

app = FastAPI(title='Salud PLC - Primera etapa', docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET, session_cookie='salud_plc_session', max_age=7200, same_site='lax', https_only=os.getenv('COOKIE_SECURE', '0') == '1')
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
templates.env.globals['roles'] = ROLES

FACILITIES = ['CESFAM Padre Las Casas', 'CESFAM Las Colinas', 'CESFAM Pulmahue', 'CESFAM Conunhuenu', 'SAR Padre Las Casas', 'Centro Comunitario de Rehabilitación (CCR)', 'Otro establecimiento / no sé']
CATEGORIES = ['Atención', 'Trato', 'Información', 'Accesibilidad', 'Tiempos de espera', 'Farmacia', 'Otro']
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
    notice = db.scalar(select(Notice).order_by(Notice.id.desc()).limit(1))
    return dict(request=request, csrf_token=csrf_for(request), current_user=user, notice=notice, facilities=FACILITIES, categories=CATEGORIES, states=STATES, types=TYPES, **extras)

def render(request, db, template, status_code=200, **extras):
    return templates.TemplateResponse(request=request, name=template, context=context(request, db, **extras), status_code=status_code)

def current_user(request: Request, db: Session):
    uid = request.session.get('staff_id')
    if not isinstance(uid, int):
        return None
    staff = db.get(Staff, uid)
    return staff if staff and staff.active else None

def user_required(request: Request, db: Session):
    user = current_user(request, db)
    if not user:
        raise HTTPException(303, headers={'Location': '/funcionarios/login'})
    return user

def permitted_cases(db, staff):
    q = select(Case).order_by(Case.created_at.desc(), Case.id.desc())
    if staff.role not in ('admin', 'jefatura'):
        q = q.where(Case.unit_id == staff.unit_id)
    return list(db.scalars(q))

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
    category = validate_one(form_str(form, 'category'), CATEGORIES, 'Categoría')
    source_area = form_str(form, 'source_area', 100) or 'Sin especificar'
    description = form_str(form, 'description', 500)
    if len(description) < 15:
        return render(request, db, 'solicitud.html', status_code=400, error='Describe tu experiencia con al menos 15 caracteres.', selected_type=case_type)
    unit = db.scalar(select(Unit).where(Unit.name == 'Mesa de entrada'))
    if not unit:
        raise HTTPException(503, 'No existe una unidad receptora configurada')
    folio = new_folio()
    token = new_tracking_code()
    case = Case(folio=folio, tracking_hmac=tracking_hash(token), case_type=case_type, facility=facility, category=category, source_area=source_area, description=description, status='Recibido', unit_id=unit.id)
    case.events.append(CaseEvent(action='Registro recibido', note='Ingresado mediante portal ciudadano'))
    db.add(case)
    db.commit()
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
    aspect = validate_one(form_str(form, 'aspect'), CATEGORIES, 'Aspecto')
    db.add(Survey(rating=int(rating_str), facility=facility, aspect=aspect))
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
    return render(request, db, 'login.html')

@app.post('/funcionarios/login')
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    limit_rate(request, 'login', 6, 300)
    email = form_str(form, 'email', 255).lower()
    pwd = form_str(form, 'password', 200)
    user = db.scalar(select(Staff).where(Staff.email == email))
    if not user or not user.active or not verify_password(user.password_hash, pwd):
        return render(request, db, 'login.html', status_code=401, error='Correo o contraseña incorrectos.')
    request.session.clear()
    request.session['staff_id'] = user.id
    csrf_for(request)
    return RedirectResponse('/funcionarios/panel', status_code=303)

@app.post('/funcionarios/salir')
async def logout(request: Request):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    request.session.clear()
    return RedirectResponse('/', status_code=303)

@app.get('/funcionarios/panel', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role == 'contenidos':
        return RedirectResponse('/funcionarios/avisos', status_code=303)
    cases = permitted_cases(db, user)
    totals = {'total': len(cases), 'open': sum(c.status != 'Cerrado' for c in cases), 'closed': sum(c.status == 'Cerrado' for c in cases)}
    return render(request, db, 'panel.html', user=user, cases=cases, totals=totals)

@app.get('/funcionarios/casos/{case_id}', response_class=HTMLResponse)
def case_detail(case_id: int, request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    case = db.get(Case, case_id)
    if not case or not can_view_case(user, case):
        raise HTTPException(404, 'Caso no disponible')
    units = list(db.scalars(select(Unit).where(Unit.active == True).order_by(Unit.name)))
    return render(request, db, 'caso_detalle.html', user=user, case=case, units=units, can_edit=can_edit_case(user, case), can_assign=can_reassign(user))

@app.post('/funcionarios/casos/{case_id}/actualizar')
async def update_case(case_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    case = db.get(Case, case_id)
    if not case or not can_edit_case(user, case):
        raise HTTPException(403, 'No tienes autorización para modificar el caso')
    status = validate_one(form_str(form, 'status'), STATES, 'Estado')
    note = form_str(form, 'note', 500)
    unit_id = case.unit_id
    if can_reassign(user):
        try: unit_id = int(form_str(form, 'unit_id', 10))
        except ValueError: raise HTTPException(400, 'Unidad inválida')
        unit = db.get(Unit, unit_id)
        if not unit or not unit.active:
            raise HTTPException(400, 'Unidad no disponible')
    if status == case.status and unit_id == case.unit_id and not note:
        return RedirectResponse(f'/funcionarios/casos/{case.id}', status_code=303)
    action = f'Estado {case.status} → {status}' if status != case.status else 'Seguimiento registrado'
    if unit_id != case.unit_id: action += ' · Derivación de unidad'
    case.status = status
    case.unit_id = unit_id
    case.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(CaseEvent(case_id=case.id, actor_id=user.id, action=action, note=note))
    db.commit()
    # Si recepción deriva a otra unidad, pierde acceso al caso de forma inmediata.
    destino = f'/funcionarios/casos/{case.id}?guardado=1' if can_view_case(user, case) else '/funcionarios/panel'
    return RedirectResponse(destino, status_code=303)

@app.get('/funcionarios/reportes', response_class=HTMLResponse)
def reports(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role == 'contenidos': raise HTTPException(403, 'Acceso denegado')
    cases = permitted_cases(db, user)
    by_type = [(name, sum(c.case_type == name for c in cases)) for name in TYPES]
    by_status = [(name, sum(c.status == name for c in cases)) for name in STATES]
    ratings = list(db.scalars(select(Survey.rating))) if user.role in ('admin', 'jefatura') else []
    avg = round(sum(ratings)/len(ratings), 1) if ratings else None
    return render(request, db, 'reportes.html', user=user, by_type=by_type, by_status=by_status, avg=avg, survey_count=len(ratings))

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
        return render(request, db, 'unidades.html', status_code=400, units=list(db.scalars(select(Unit))), error='Nombre inválido o ya existente.')
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
    if (len(name) < 3 or '@' not in email or len(pwd) < 12 or role not in ROLES or not db.get(Unit, unit_id) or db.scalar(select(Staff).where(Staff.email == email))):
        return render(request, db, 'equipo.html', status_code=400, error='Revisa los datos: correo único, contraseña de al menos 12 caracteres, rol y unidad válidos.', users=list(db.scalars(select(Staff))), units=list(db.scalars(select(Unit))))
    db.add(Staff(full_name=name, email=email, password_hash=hash_password(pwd), role=role, unit_id=unit_id, active=True))
    db.commit()
    return RedirectResponse('/funcionarios/equipo', status_code=303)

@app.get('/funcionarios/avisos', response_class=HTMLResponse)
def notices_page(request: Request, db: Session = Depends(get_db)):
    user = user_required(request, db)
    if user.role not in ('admin', 'contenidos'): raise HTTPException(403, 'Acceso restringido')
    notice = db.scalar(select(Notice).order_by(Notice.id.desc()).limit(1))
    return render(request, db, 'avisos.html', text=notice.text if notice else '')

@app.post('/funcionarios/avisos')
async def update_notice(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form.get('csrf_token'))
    user = user_required(request, db)
    if user.role not in ('admin', 'contenidos'): raise HTTPException(403, 'Acceso restringido')
    text = form_str(form, 'text', 500)
    db.add(Notice(text=text, editor_id=user.id))
    db.commit()
    return RedirectResponse('/funcionarios/avisos?guardado=1', status_code=303)
