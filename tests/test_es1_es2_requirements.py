"""Regresión de promesas ES1/ES2: informes filtrables, catálogo administrable y alcance por rol."""
from datetime import datetime

from app.database import SessionLocal
from app.models import Audit, Case, Category
from test_workflow import create_case, csrf, login, logout


def test_report_filters_by_inclusive_period_category_and_type(client):
    folio_old, _ = create_case(client)
    folio_today, _ = create_case(client)
    with SessionLocal() as db:
        old = db.query(Case).filter_by(folio=folio_old).one()
        old.created_at = datetime(2025, 1, 1, 11, 15)
        today = db.query(Case).filter_by(folio=folio_today).one()
        today.created_at = datetime(2026, 11, 17, 23, 59, 59)
        db.commit()
    login(client, 'admin@prueba.local')
    report = client.get('/funcionarios/reportes?desde=2026-11-17&hasta=2026-11-17&category=Trato&case_type=Reclamo')
    assert report.status_code == 200
    assert '<strong>1</strong> solicitudes encontradas' in report.text
    assert 'value="2026-11-17"' in report.text
    report_old = client.get('/funcionarios/reportes?hasta=2025-01-01&category=Trato')
    assert '<strong>1</strong> solicitudes encontradas' in report_old.text
    report_wrong = client.get('/funcionarios/reportes?category=Farmacia')
    assert '<strong>0</strong> solicitudes encontradas' in report_wrong.text


def test_report_invalid_dates_and_categories_render_html_not_json(client):
    login(client, 'admin@prueba.local')
    for url in ('/funcionarios/reportes?desde=2026-02-30',
                '/funcionarios/reportes?desde=2026-12-01&hasta=2026-11-01',
                '/funcionarios/reportes?desde=13-11-2026',
                '/funcionarios/reportes?category=Desconocida'):
        response = client.get(url)
        assert response.status_code == 400, (url, response.text[:200])
        assert 'text/html' in response.headers['content-type']
        assert '<html' in response.text.lower()


def test_report_respects_unit_scope_before_filtering(client):
    create_case(client)
    login(client, 'farmacia@prueba.local')
    response = client.get('/funcionarios/reportes?category=Trato')
    assert response.status_code == 200
    assert '<strong>0</strong> solicitudes encontradas' in response.text
    logout(client)
    login(client, 'jefatura@prueba.local')
    response = client.get('/funcionarios/reportes?category=Trato')
    assert '<strong>1</strong> solicitudes encontradas' in response.text


def test_admin_creates_category_used_by_public_forms_and_reports(client):
    login(client, 'admin@prueba.local')
    creation = client.post('/funcionarios/categorias', data={
        'csrf_token': csrf(client, '/funcionarios/categorias'), 'name': 'Transporte sanitario'})
    assert creation.status_code == 200
    with SessionLocal() as db:
        category = db.query(Category).filter_by(name='Transporte sanitario').one()
        assert category.active
        assert db.query(Audit).filter_by(event_type='categoria_creada').count() == 1
    assert 'Transporte sanitario' in client.get('/solicitud').text
    assert 'Transporte sanitario' in client.get('/encuesta').text
    token = csrf(client, '/solicitud')
    registered = client.post('/solicitud', data={
        'csrf_token': token, 'case_type': 'Sugerencia', 'facility': 'CESFAM Las Colinas',
        'category': 'Transporte sanitario', 'description': 'Mejorar la orientación sobre transporte sanitario.'})
    assert registered.status_code == 200
    report = client.get('/funcionarios/reportes?category=Transporte%20sanitario&case_type=Sugerencia')
    assert '<strong>1</strong> solicitudes encontradas' in report.text


def test_disabled_category_disappears_from_input_but_preserves_history(client):
    folio, _ = create_case(client)
    login(client, 'admin@prueba.local')
    with SessionLocal() as db:
        category_id = db.query(Category).filter_by(name='Trato').one().id
        case_id = db.query(Case).filter_by(folio=folio).one().id
    response = client.post(f'/funcionarios/categorias/{category_id}/estado', data={
        'csrf_token': csrf(client, '/funcionarios/categorias')})
    assert response.status_code == 200
    assert '<option value="Trato"' not in client.get('/solicitud').text
    assert '<option value="Trato"' not in client.get('/encuesta').text
    assert 'Trato (histórica, desactivada)' in client.get(f'/funcionarios/casos/{case_id}').text
    report = client.get('/funcionarios/reportes?category=Trato')
    assert '<strong>1</strong> solicitudes encontradas' in report.text
    rejected = client.post('/solicitud', data={
        'csrf_token': csrf(client, '/solicitud'), 'case_type': 'Reclamo',
        'facility': 'CESFAM Las Colinas', 'category': 'Trato',
        'description': 'Este registro ya no puede utilizar esa categoría.'})
    assert rejected.status_code == 400
    assert 'Categoría inválido' in rejected.text
    with SessionLocal() as db:
        assert db.query(Case).filter_by(folio=folio).count() == 1


def test_category_permissions_duplicate_csrf_and_other_mandatory(client):
    login(client, 'mesa@prueba.local')
    assert client.get('/funcionarios/categorias').status_code == 403
    token = csrf(client, '/funcionarios/panel')
    assert client.post('/funcionarios/categorias', data={'csrf_token': token, 'name': 'Otra unidad'}).status_code == 403
    logout(client)
    login(client, 'admin@prueba.local')
    assert client.post('/funcionarios/categorias', data={'csrf_token': 'incorrecto', 'name': 'Nuevo motivo'}).status_code == 403
    assert client.post('/funcionarios/categorias', data={
        'csrf_token': csrf(client, '/funcionarios/categorias'), 'name': 'trato'}).status_code == 400
    with SessionLocal() as db:
        otro_id = db.query(Category).filter_by(name='Otro').one().id
    mandatory = client.post(f'/funcionarios/categorias/{otro_id}/estado', data={
        'csrf_token': csrf(client, '/funcionarios/categorias')})
    assert mandatory.status_code == 400
    with SessionLocal() as db:
        assert db.get(Category, otro_id).active is True


def test_report_multiple_queries_without_cross_session_leak(client):
    """Prueba de repetición local: no es prueba de carga de producción."""
    create_case(client)
    login(client, 'jefatura@prueba.local')
    for _ in range(30):
        response = client.get('/funcionarios/reportes?category=Trato')
        assert response.status_code == 200
        assert '<strong>1</strong> solicitudes encontradas' in response.text
    logout(client)
    blocked = client.get('/funcionarios/reportes?category=Trato', follow_redirects=False)
    assert blocked.status_code == 303
    assert blocked.headers['location'].startswith('/funcionarios/login?sesion=')
