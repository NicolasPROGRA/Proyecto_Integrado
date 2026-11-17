"""Verificaciones del modelo ER de 14 tablas y los flujos que lo utilizan."""
import re

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from app.database import SessionLocal, engine, Base
from app.models import (
    Audit, Case, CaseEvent, Citizen, Role, Staff, RecordType,
    Channel, Category, CaseStatus, Survey, SurveyQuestion, Attachment, Unit,
)
from test_workflow import create_case, csrf, login


EXPECTED_TABLES = {
    'rol', 'unidad', 'usuario_admin', 'tipo_registro', 'canal', 'categoria',
    'estado_caso', 'ciudadano', 'registro', 'seguimiento', 'pregunta_encuesta',
    'respuesta_encuesta', 'adjunto', 'auditoria',
}


def test_14_tablas_implementadas_y_catalogos_cargados(client):
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES
    with SessionLocal() as db:
        assert db.query(Role).count() == 6
        assert db.query(RecordType).count() == 4
        assert db.query(Channel).count() == 1
        assert db.query(Category).count() == 7
        assert db.query(CaseStatus).count() == 4
        assert db.query(SurveyQuestion).count() >= 1
    for table in EXPECTED_TABLES:
        assert inspector.get_pk_constraint(table)['constrained_columns']


def test_registro_usa_claves_foraneas_y_auditoria(client):
    folio, _ = create_case(client)
    with SessionLocal() as db:
        case = db.scalar(select(Case).where(Case.folio == folio))
        assert case.case_type == 'Reclamo'
        assert case.category == 'Trato'
        assert case.status == 'Recibido'
        assert case.record_type_id and case.channel_id and case.category_id and case.status_id
        assert case.unit_id and case.id
        assert db.query(CaseEvent).filter_by(case_id=case.id).count() == 1
        assert db.query(Audit).filter_by(record_id=case.id, event_type='registro_creado').count() == 1


def test_respuesta_encuesta_depende_de_registro_y_pregunta(client):
    response = client.post('/encuesta', data=dict(
        csrf_token=csrf(client, '/encuesta'), rating='4',
        facility='CESFAM Padre Las Casas', aspect='Trato',
    ))
    assert response.status_code == 200
    with SessionLocal() as db:
        answer = db.scalar(select(Survey))
        assert answer.record.case_type == 'Encuesta'
        assert answer.record.status is None
        assert answer.record.category == 'Trato'
        assert answer.question.code == 'SAT_GENERAL'
    login(client, 'admin@prueba.local')
    assert '0 resultados' in client.get('/funcionarios/panel').text


def test_rol_es_una_referencia_y_rechaza_rol_inexistente(client):
    with SessionLocal() as db:
        admin = db.scalar(select(Staff).where(Staff.email == 'admin@prueba.local'))
        assert admin.role == 'admin'
        assert admin.role_record.label == 'Administración general'
        db.add(Staff(full_name='Sin rol', email='sinrol@prueba.local',
                     password_hash='hash-ficticio', role_id=999999, unit_id=admin.unit_id))
        try:
            db.commit()
            assert False, 'La FK de rol aceptó un valor inexistente'
        except IntegrityError:
            db.rollback()


def test_cuadros_del_modelo_tienen_relaciones_esperadas(client):
    inspector = inspect(engine)
    foreign_keys = {fk['referred_table'] for fk in inspector.get_foreign_keys('registro')}
    assert {'tipo_registro', 'canal', 'categoria', 'estado_caso', 'ciudadano', 'unidad'} <= foreign_keys
    assert {fk['referred_table'] for fk in inspector.get_foreign_keys('respuesta_encuesta')} == {'registro', 'pregunta_encuesta'}
    assert {fk['referred_table'] for fk in inspector.get_foreign_keys('auditoria')} == {'registro', 'usuario_admin'}


def test_todas_las_tablas_generan_ddl_postgresql(client):
    assert len(Base.metadata.tables) == 14
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        statement = str(CreateTable(table).compile(dialect=dialect))
        assert 'CREATE TABLE' in statement
        assert table.name in statement
    audit_ddl = str(CreateTable(Base.metadata.tables['auditoria']).compile(dialect=dialect))
    assert 'JSONB' in audit_ddl


def test_contacto_voluntario_y_adjunto_con_descarga_por_rol(client, tmp_path, monkeypatch):
    import app.main as web
    monkeypatch.setattr(web, 'PRIVATE_DIR', tmp_path)
    result = client.post('/solicitud', data={
        'csrf_token': csrf(client, '/solicitud'), 'case_type': 'Reclamo',
        'facility': 'CESFAM Padre Las Casas', 'category': 'Trato',
        'description': 'Solicitud ficticia con respaldo documental no sensible.',
        'contact_name': 'Persona Ficticia', 'contact_email': 'ficticia@example.test',
        'contact_consent': 'on',
    }, files={'attachment': ('ejemplo.pdf', b'%PDF-1.4\nEvidencia ficticia', 'application/pdf')})
    assert result.status_code == 200
    folio = re.search(r'id="folio-text">([^<]+)', result.text).group(1)
    with SessionLocal() as db:
        case = db.scalar(select(Case).where(Case.folio == folio))
        assert case.citizen.contact_consent is True
        assert case.citizen.email == 'ficticia@example.test'
        attachment = case.attachments[0]
        attachment_id = attachment.id
        assert attachment.original_filename == 'ejemplo.pdf'
        assert (tmp_path / attachment.storage_key).is_file()
        case_id = case.id
    assert client.get(f'/funcionarios/adjuntos/{attachment_id}', follow_redirects=False).status_code == 303
    login(client, 'farmacia@prueba.local')
    assert client.get(f'/funcionarios/adjuntos/{attachment_id}').status_code == 404
    client.post('/funcionarios/salir', data={'csrf_token': csrf(client, '/funcionarios/panel')})
    login(client, 'mesa@prueba.local')
    assert 'ejemplo.pdf' in client.get(f'/funcionarios/casos/{case_id}').text
    download = client.get(f'/funcionarios/adjuntos/{attachment_id}')
    assert download.status_code == 200 and download.content.startswith(b'%PDF-1.4')


def test_contacto_sin_permiso_y_adjunto_invalido_rechazados(client):
    base = {
        'csrf_token': csrf(client, '/solicitud'), 'case_type': 'Sugerencia',
        'facility': 'CESFAM Padre Las Casas', 'category': 'Trato',
        'description': 'Solicitud ficticia destinada a validar controles de entrada.',
    }
    denied = client.post('/solicitud', data={**base, 'contact_email': 'x@example.test'})
    assert denied.status_code == 400
    invalid = client.post('/solicitud', data=base,
        files={'attachment': ('falso.pdf', b'Archivo no es PDF', 'application/pdf')})
    assert invalid.status_code == 400
    with SessionLocal() as db:
        assert db.query(Citizen).count() == 0
        assert db.query(Attachment).count() == 0
        assert db.query(Case).count() == 0
