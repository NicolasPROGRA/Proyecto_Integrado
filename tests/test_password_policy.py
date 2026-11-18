"""Validación de la política de complejidad al crear cuentas nuevas."""
import html
import re

import pytest

from app.database import SessionLocal
from app.models import Staff, Unit
from app.security import PASSWORD_POLICY_MESSAGE, valid_new_password


@pytest.mark.parametrize('password', [
    '123456789012',
    'solominusculas123!',
    'SOLOMAYUSCULAS123!',
    'SinNumeroNiClave!',
    'SinSimbolo2026',
    'Corta1!Aa',
    'Con Espacios 2026Aa',
])
def test_insecure_password_rejected_by_shared_policy(password):
    assert not valid_new_password(password)


def test_secure_password_accepted_by_shared_policy():
    assert valid_new_password('ClaveSegura2026!')
    assert valid_new_password('ContraseñaÑ2026#')


def _csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200
    token = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert token
    return html.unescape(token.group(1))


def test_staff_password_policy_enforced_on_server(client):
    login = client.post('/funcionarios/login', data={
        'csrf_token': _csrf(client, '/funcionarios/login'),
        'email': 'admin@prueba.local', 'password': 'ClaveDePrueba2026!',
    })
    assert login.status_code == 200

    with SessionLocal() as db:
        unit_id = db.query(Unit).filter_by(name='Farmacia').one().id

    form = {
        'name': 'Funcionario Política', 'email': 'politica@prueba.local',
        'role': 'funcionario', 'unit_id': str(unit_id),
    }
    page = client.get('/funcionarios/equipo')
    assert 'data-password-policy="complex"' in page.text

    invalid = client.post('/funcionarios/equipo', data={
        **form, 'csrf_token': _csrf(client, '/funcionarios/equipo'),
        'password': '123456789012',
    })
    assert invalid.status_code == 400
    assert PASSWORD_POLICY_MESSAGE in invalid.text
    with SessionLocal() as db:
        assert db.query(Staff).filter_by(email=form['email']).count() == 0

    valid = client.post('/funcionarios/equipo', data={
        **form, 'csrf_token': _csrf(client, '/funcionarios/equipo'),
        'password': 'ClaveSegura2026!',
    })
    assert valid.status_code == 200
    with SessionLocal() as db:
        assert db.query(Staff).filter_by(email=form['email']).count() == 1
