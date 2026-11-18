import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

# La BD de pruebas se separa de la BD utilizada por el usuario.
_testing_dir = tempfile.TemporaryDirectory(prefix='plc_test_')
os.environ['DATABASE_URL'] = f"sqlite:///{Path(_testing_dir.name) / 'test.sqlite3'}"
from app.database import Base, engine, init_database, SessionLocal
from app.main import app, _attempts
from app.models import Staff, Unit, Role
from app.security import hash_password

@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    init_database()
    _attempts.clear()
    with SessionLocal() as db:
        units = {u.name: u for u in db.query(Unit).all()}
        roles = {r.code: r for r in db.query(Role).all()}
        db.add_all([
            Staff(full_name='Admin de Pruebas', email='admin@prueba.local', password_hash=hash_password('ClaveDePrueba2026!'), role_id=roles['admin'].id, unit_id=units['Dirección'].id),
            Staff(full_name='Recepción de Pruebas', email='mesa@prueba.local', password_hash=hash_password('ClaveDePrueba2026!'), role_id=roles['recepcion'].id, unit_id=units['Mesa de entrada'].id),
            Staff(full_name='Farmacia de Pruebas', email='farmacia@prueba.local', password_hash=hash_password('ClaveDePrueba2026!'), role_id=roles['funcionario'].id, unit_id=units['Farmacia'].id),
            Staff(full_name='Jefatura de Pruebas', email='jefatura@prueba.local', password_hash=hash_password('ClaveDePrueba2026!'), role_id=roles['jefatura'].id, unit_id=units['Dirección'].id),
        ])
        db.commit()
    with TestClient(app, follow_redirects=True) as client:
        yield client


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    _testing_dir.cleanup()