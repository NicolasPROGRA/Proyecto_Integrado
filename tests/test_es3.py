"""Pruebas adicionales de integración, bordes, permisos e integridad para la ES3."""
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine
from app.models import (Case, CaseEvent, Survey, Unit, RecordType, Channel,
                        Category, CaseStatus, SurveyQuestion)
from test_workflow import create_case, csrf, login, logout


def test_invalid_public_case_is_not_saved(client):
    token = csrf(client, '/solicitud')
    with SessionLocal() as db:
        before = db.query(Case).count()
    for category, description in [('No existe', 'Descripción de prueba de veinte caracteres'),
                                  ('Trato', 'Muy corto')]:
        result = client.post('/solicitud', data=dict(
            csrf_token=token, case_type='Reclamo', facility='CESFAM Padre Las Casas',
            category=category, description=description))
        assert result.status_code == 400
    with SessionLocal() as db:
        assert db.query(Case).count() == before


def test_invalid_survey_is_not_persisted(client):
    token = csrf(client, '/encuesta')
    response = client.post('/encuesta', data=dict(csrf_token=token, rating='6',
        facility='CESFAM Padre Las Casas', aspect='Trato'))
    assert response.status_code == 400
    with SessionLocal() as db:
        assert db.query(Survey).count() == 0


def test_filters_do_not_reveal_cases_from_other_units(client):
    folio, _ = create_case(client)
    login(client, 'farmacia@prueba.local')
    for suffix in ['', f'?q={folio}', '?category=Trato', '?status=Recibido']:
        response = client.get('/funcionarios/panel' + suffix)
        assert response.status_code == 200
        # El texto buscado sí aparece en el campo de filtro; nunca en el listado.
        assert f'<strong>{folio}</strong>' not in response.text
    logout(client)
    login(client, 'admin@prueba.local')
    response = client.get(f'/funcionarios/panel?q={folio}&category=Trato&status=Recibido')
    assert response.status_code == 200 and folio in response.text


def test_reclassification_persists_and_is_audited(client):
    folio, _ = create_case(client)
    with SessionLocal() as db:
        case_id = db.query(Case).filter_by(folio=folio).one().id
    login(client, 'mesa@prueba.local')
    response = client.post(f'/funcionarios/casos/{case_id}/actualizar', data=dict(
        csrf_token=csrf(client, f'/funcionarios/casos/{case_id}'),
        status='En proceso', category='Farmacia', note='Reclasificado tras revisión'))
    assert response.status_code == 200
    with SessionLocal() as db:
        case = db.get(Case, case_id)
        assert (case.status, case.category) == ('En proceso', 'Farmacia')
        assert any('Clasificación Trato' in event.action for event in case.events)
        assert any('Reclasificado tras revisión' == event.note for event in case.events)
    report = client.get('/funcionarios/reportes')
    assert 'Motivos de atención' in report.text and 'Farmacia' in report.text


def test_reclassification_rejects_unlisted_category(client):
    folio, _ = create_case(client)
    with SessionLocal() as db:
        case_id = db.query(Case).filter_by(folio=folio).one().id
    login(client, 'mesa@prueba.local')
    response = client.post(f'/funcionarios/casos/{case_id}/actualizar', data=dict(
        csrf_token=csrf(client, f'/funcionarios/casos/{case_id}'),
        status='Cerrado', category='No registrado'))
    assert response.status_code == 400
    with SessionLocal() as db:
        assert db.get(Case, case_id).status == 'Recibido'


def test_invalid_filters_and_pages_have_no_effect(client):
    login(client, 'admin@prueba.local')
    for suffix, expected in [('?category=NoExiste', 400), ('?page=0', 400),
                             ('?page=999', 404), ('?page=abc', 400),
                             ('?q='+'x'*81, 400)]:
        assert client.get('/funcionarios/panel' + suffix).status_code == expected


def test_literal_wildcards_do_not_match_everything(client):
    create_case(client)
    login(client, 'admin@prueba.local')
    result = client.get('/funcionarios/panel?q=%25')
    assert '0 resultados' in result.text


def test_pagination_caps_list_and_preserves_search(client):
    with SessionLocal() as db:
        unit = db.query(Unit).filter_by(name='Mesa de entrada').one()
        kind = db.query(RecordType).filter_by(name='Reclamo').one()
        channel = db.query(Channel).filter_by(name='Portal web').one()
        category = db.query(Category).filter_by(name='Trato').one()
        status = db.query(CaseStatus).filter_by(name='Recibido').one()
        for number in range(23):
            db.add(Case(folio=f'PLC-PAGE{number:04d}', tracking_hmac='a'*64,
                record_type_id=kind.id, channel_id=channel.id,
                facility='CESFAM Padre Las Casas', category_id=category.id,
                description='Registro de prueba paginación', unit_id=unit.id, status_id=status.id))
        db.commit()
    login(client, 'mesa@prueba.local')
    first = client.get('/funcionarios/panel')
    second = client.get('/funcionarios/panel?page=2')
    assert 'Página 1 de 2' in first.text
    assert 'Página 2 de 2' in second.text
    assert first.text.count('class="case-pill"') == 20
    assert second.text.count('class="case-pill"') == 3


def test_survey_statistics_are_restricted_by_role(client):
    for rating in [3, 5]:
        assert client.post('/encuesta', data=dict(csrf_token=csrf(client, '/encuesta'),
            rating=str(rating), facility='CESFAM Padre Las Casas', aspect='Trato')).status_code == 200
    login(client, 'mesa@prueba.local')
    assert 'Satisfacción usuaria' not in client.get('/funcionarios/reportes').text
    logout(client)
    login(client, 'jefatura@prueba.local')
    page = client.get('/funcionarios/reportes').text
    assert 'Satisfacción usuaria' in page and '4.0' in page and '2</strong> encuestas' in page


def test_database_rejects_invalid_domain_and_foreign_keys(client):
    with SessionLocal() as db:
        foreign_keys = db.execute(text('PRAGMA foreign_keys')).scalar_one()
        assert foreign_keys == 1
        kind = db.query(RecordType).filter_by(name='Reclamo').one()
        channel = db.query(Channel).filter_by(name='Portal web').one()
        category = db.query(Category).filter_by(name='Trato').one()
        status = db.query(CaseStatus).filter_by(name='Recibido').one()
        question = db.query(SurveyQuestion).filter_by(code='SAT_GENERAL').one()
        survey_record = Case(folio='PLC-TESTSURVEY', tracking_hmac='a'*64,
            record_type_id=kind.id, channel_id=channel.id, facility='CESFAM Padre Las Casas')
        db.add(survey_record)
        db.flush()
        db.add(Survey(rating=0, record_id=survey_record.id, question_id=question.id))
        try:
            db.commit()
            assert False, 'Se aceptó una encuesta fuera de escala'
        except IntegrityError:
            db.rollback()
        db.add(Case(folio='PLC-BADUNIT', tracking_hmac='a'*64,
            record_type_id=kind.id, channel_id=channel.id,
            facility='CESFAM Padre Las Casas', category_id=category.id,
            description='Intento de FK inválida', unit_id=999999, status_id=status.id))
        try:
            db.commit()
            assert False, 'Se aceptó una FK inexistente'
        except IntegrityError:
            db.rollback()
        unit = db.query(Unit).filter_by(name='Mesa de entrada').one()
        db.add(Case(folio='PLC-BADSTATUS', tracking_hmac='a'*64,
            record_type_id=kind.id, channel_id=channel.id,
            facility='CESFAM Padre Las Casas', category_id=category.id,
            description='Estado inválido', unit_id=unit.id, status_id=999999))
        try:
            db.commit()
            assert False, 'Se aceptó un estado fuera del catálogo'
        except IntegrityError:
            db.rollback()


def test_database_has_operational_indexes(client):
    indexes = {idx['name'] for idx in inspect(engine).get_indexes('registro')}
    assert {'ix_registro_unidad_estado_fecha', 'ix_registro_tipo_categoria_fecha', 'ix_registro_folio'} <= indexes
