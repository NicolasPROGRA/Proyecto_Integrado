"""Regresión de controles del navegador, sesiones y validación de origen."""
import base64
import json
from datetime import datetime, timezone

from itsdangerous import TimestampSigner
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Audit, Case
from app.security import APP_SECRET
from test_workflow import create_case, csrf, login


COOKIE = 'salud_plc_session'


def test_public_pages_show_citizen_text_not_development_notices(client):
    for path in ('/', '/solicitud', '/encuesta', '/funcionarios/login'):
        response = client.get(path)
        assert response.status_code == 200
        for old_text in ('ENTORNO ACADÉMICO DE DESARROLLO',
                         'Proyecto académico en desarrollo', 'base de datos local de pruebas',
                         'cuenta institucional de desarrollo', 'correo ficticios'):
            assert old_text not in response.text, (path, old_text)
    assert 'Atención usuaria' in client.get('/').text
    survey = client.post('/encuesta', data={
        'csrf_token': csrf(client, '/encuesta'), 'rating': '5',
        'facility': 'CESFAM Las Colinas', 'aspect': 'Atención'})
    assert survey.status_code == 200
    assert 'base de datos local de pruebas' not in survey.text
    registered = client.post('/solicitud', data={
        'csrf_token': csrf(client, '/solicitud'), 'case_type': 'Reclamo',
        'facility': 'CESFAM Las Colinas', 'category': 'Trato',
        'description': 'Se necesita mejorar la orientación sobre el horario de atención.'})
    assert registered.status_code == 200
    assert 'base de datos local de desarrollo' not in registered.text
    assert 'código privado se muestra una sola vez' in registered.text


def test_security_headers_enforce_external_script_and_frame_restrictions(client):
    for path in ('/', '/solicitud', '/funcionarios/login', '/funcionarios/panel'):
        response = client.get(path)
        assert response.headers['x-frame-options'] == 'DENY'
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['referrer-policy'] == 'no-referrer'
        csp = response.headers['content-security-policy']
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "form-action 'self'" in csp
    error_page = client.get('/ruta-inexistente')
    assert error_page.status_code == 404
    assert 'onclick=' not in error_page.text


def test_cross_site_origin_is_rejected_even_with_valid_csrf(client):
    token = csrf(client, '/solicitud')
    data = {'csrf_token': token, 'case_type': 'Reclamo', 'facility': 'CESFAM Padre Las Casas',
            'category': 'Trato', 'description': 'Datos ficticios para verificar CSRF y origen.'}
    rejected = client.post('/solicitud', data=data, headers={
        'Origin': 'https://sitio-malicioso.invalid', 'Sec-Fetch-Site': 'cross-site'})
    assert rejected.status_code == 403
    assert 'sitio no autorizado' in rejected.text
    rejected_without_origin = client.post('/solicitud', data=data, headers={
        'Sec-Fetch-Site': 'cross-site'})
    assert rejected_without_origin.status_code == 403
    with SessionLocal() as db:
        assert db.query(Case).count() == 0
    accepted = client.post('/solicitud', data=data, headers={'Origin': 'http://testserver'})
    assert accepted.status_code == 200
    # Navegadores modernos indican same-origin aun cuando un proxy local
    # reconstruye la dirección de destino con otro host.
    accepted_browser = client.post('/solicitud', data=data, headers={
        'Origin': 'http://127.0.0.1:8000', 'Sec-Fetch-Site': 'same-origin'})
    assert accepted_browser.status_code == 200
    accepted_loopback = client.post('/solicitud', data=data, headers={
        'Host': '127.0.0.1:8000', 'Origin': 'http://localhost:8000'})
    assert accepted_loopback.status_code == 200
    # En el servidor Windows limitado a loopback, un proxy/extensión local
    # puede informar un Origin distinto. Se conserva la comprobación del token.
    with TestClient(app, base_url='http://127.0.0.1:8000',
                    client=('127.0.0.1', 55000)) as local_client:
        local_data = dict(data, csrf_token=csrf(local_client, '/solicitud'))
        local_sent = local_client.post('/solicitud', data=local_data, headers={
            'Origin': 'http://localhost:9090', 'Sec-Fetch-Site': 'cross-site'})
        assert local_sent.status_code == 200
        local_bad_token = local_client.post('/solicitud',
                                            data=dict(local_data, csrf_token='invalido'),
                                            headers={'Origin': 'http://localhost:9090'})
        assert local_bad_token.status_code == 403
    with SessionLocal() as db:
        assert db.query(Case).count() == 4


def test_revoked_session_cookie_cannot_be_replayed_after_logout(client):
    login(client, 'admin@prueba.local')
    old_cookie = client.cookies.get(COOKIE)
    assert old_cookie
    closed = client.post('/funcionarios/salir',
                         data={'csrf_token': csrf(client, '/funcionarios/panel')})
    assert 'Cerraste sesión correctamente' in closed.text
    with SessionLocal() as db:
        assert db.query(Audit).filter_by(event_type='inicio_sesion').count() == 1
        assert db.query(Audit).filter_by(event_type='cierre_sesion').count() == 1
    client.cookies.set(COOKIE, old_cookie)
    response = client.get('/funcionarios/panel', follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/funcionarios/login?sesion=finalizada'
    assert client.get('/funcionarios/sesion-actual').status_code == 401


def test_session_inactive_more_than_half_hour_requires_new_login(client):
    login(client, 'admin@prueba.local')
    old_cookie = client.cookies.get(COOKIE)
    signer = TimestampSigner(APP_SECRET)
    payload = json.loads(base64.b64decode(signer.unsign(old_cookie)))
    payload['last_seen'] = datetime.now(timezone.utc).timestamp() - 31 * 60
    expired_cookie = signer.sign(base64.b64encode(json.dumps(payload).encode())).decode()
    client.cookies.set(COOKIE, expired_cookie)
    response = client.get('/funcionarios/reportes', follow_redirects=False)
    assert response.status_code == 303
    assert 'sesion=finalizada' in response.headers['location']


def test_failed_login_is_audited_without_storing_password(client):
    response = client.post('/funcionarios/login', data={
        'csrf_token': csrf(client, '/funcionarios/login'),
        'email': 'admin@prueba.local', 'password': 'ClaveIncorrecta!234'})
    assert response.status_code == 401
    assert 'Correo o contraseña incorrectos' in response.text
    with SessionLocal() as db:
        events = db.query(Audit).filter_by(event_type='inicio_sesion_fallido').all()
        assert len(events) == 1
        assert events[0].details == {'resultado': 'denegado'}
        assert 'ClaveIncorrecta' not in str(events[0].details)
