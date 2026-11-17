"""Regresión: ningún error habitual de formularios debe abrir JSON crudo."""
from io import BytesIO

from app.database import SessionLocal
from app.models import Case
from test_workflow import csrf


def test_missing_contact_consent_stays_inside_form(client):
    token = csrf(client, '/solicitud')
    with SessionLocal() as db:
        before = db.query(Case).count()

    response = client.post('/solicitud', data={
        'csrf_token': token,
        'case_type': 'Sugerencia',
        'facility': 'CESFAM Padre Las Casas',
        'category': 'Trato',
        'description': 'La atención fue cordial pero muy lenta en recepción.',
        'contact_name': 'Persona de prueba',
        'contact_email': 'contacto@ejemplo.cl',
    })
    assert response.status_code == 400
    assert 'text/html' in response.headers['content-type']
    assert 'aceptar el consentimiento' in response.text
    assert '<form action="/solicitud"' in response.text
    assert 'contacto@ejemplo.cl' in response.text
    assert 'Sugerencia' in response.text
    assert '"detail"' not in response.text
    with SessionLocal() as db:
        assert db.query(Case).count() == before


def test_invalid_attachment_stays_inside_form(client):
    token = csrf(client, '/solicitud')
    response = client.post('/solicitud', data={
        'csrf_token': token,
        'case_type': 'Reclamo',
        'facility': 'CESFAM Padre Las Casas',
        'category': 'Atención',
        'description': 'Una explicación suficiente para realizar una prueba.',
    }, files={'attachment': ('demasiado_grande.pdf', BytesIO(b'%PDF-' + b'a' * (2 * 1024 * 1024)), 'application/pdf')})
    assert response.status_code == 413
    assert 'text/html' in response.headers['content-type']
    assert 'supera el máximo' in response.text
    assert '<form action="/solicitud"' in response.text


def test_survey_invalid_value_stays_in_survey(client):
    token = csrf(client, '/encuesta')
    response = client.post('/encuesta', data={
        'csrf_token': token, 'rating': '6',
        'facility': 'CESFAM Padre Las Casas', 'aspect': 'Trato',
    })
    assert response.status_code == 400
    assert '<form action="/encuesta"' in response.text
    assert 'calificación' in response.text
    assert '"detail"' not in response.text


def test_rejected_navigation_uses_branded_html(client):
    csrf(client, '/solicitud')
    result = client.post('/solicitud', data={'csrf_token': 'incorrecto', 'case_type': 'Reclamo'})
    assert result.status_code == 403
    assert 'text/html' in result.headers['content-type']
    assert 'No pudimos completar esta acción' in result.text
    assert '"detail"' not in result.text


def test_frontend_validation_is_part_of_the_page(client):
    page = client.get('/solicitud')
    assert 'contact_consent' in page.text
    assert 'Si agregas un nombre o correo' in page.text
    script = client.get('/static/backend.js')
    assert script.status_code == 200
    assert 'event.preventDefault()' in script.text
    assert 'Te faltó aceptar el consentimiento' in script.text
