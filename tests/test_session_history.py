"""Pruebas de cierre de sesión e historial Atrás/Adelante del navegador."""

from app.database import SessionLocal
from app.models import Case
from test_workflow import create_case, csrf, login


def test_logout_blocks_old_panel_and_forces_login(client):
    folio, _ = create_case(client)
    login(client, 'mesa@prueba.local')
    before = client.get('/funcionarios/panel')
    assert before.status_code == 200 and folio in before.text
    assert 'no-store' in before.headers['cache-control']
    assert 'private' in before.headers['cache-control']
    assert 'data-protected-area="true"' in before.text
    assert client.get('/funcionarios/sesion-actual').status_code == 204

    token = csrf(client, '/funcionarios/panel')
    logout = client.post('/funcionarios/salir', data={'csrf_token': token}, follow_redirects=False)
    assert logout.status_code == 303
    assert logout.headers['location'] == '/funcionarios/login?cerrada=1'
    assert 'no-store' in logout.headers['cache-control']
    assert client.get('/funcionarios/sesion-actual').status_code == 401

    # El historial puede conservar la URL, pero no puede recuperar un panel autorizado.
    protected = ['/funcionarios/panel', '/funcionarios/reportes', '/funcionarios/unidades']
    with SessionLocal() as db:
        case_id = db.query(Case).filter_by(folio=folio).one().id
    protected.append(f'/funcionarios/casos/{case_id}')
    for path in protected:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers['location'] == '/funcionarios/login?sesion=finalizada'

    login_page = client.get('/funcionarios/panel')
    assert 'No puedes ingresar a Gestión porque tu sesión está cerrada' in login_page.text
    assert folio not in login_page.text


def test_session_notice_and_relogin_restore_access(client):
    login(client, 'admin@prueba.local')
    logout = client.post('/funcionarios/salir', data={
        'csrf_token': csrf(client, '/funcionarios/panel')
    })
    assert 'Cerraste sesión correctamente' in logout.text
    assert 'data-protected-area="false"' in logout.text

    login(client, 'admin@prueba.local')
    response = client.get('/funcionarios/panel')
    assert response.status_code == 200
    assert 'Panel de solicitudes' in response.text
    assert client.get('/funcionarios/sesion-actual').status_code == 204


def test_back_forward_script_and_public_sensitive_cache(client):
    script = client.get('/static/backend.js').text
    assert "window.addEventListener('pagehide'" in script
    assert "window.addEventListener('pageshow'" in script
    assert "window.location.replace('/funcionarios/login?sesion=finalizada')" in script
    assert 'private-page-hidden' in script
    assert 'no-store' in client.get('/solicitud').headers['cache-control']
    assert 'no-store' in client.get('/seguimiento').headers['cache-control']
