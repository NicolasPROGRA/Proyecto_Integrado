import html
import re
from app.database import SessionLocal
from app.models import Case, CaseEvent, Survey, Unit

def csrf(client, path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code, r.text[:100])
    found = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert found, path
    return html.unescape(found.group(1))

def create_case(client):
    r = client.post('/solicitud', data=dict(csrf_token=csrf(client, '/solicitud'),case_type='Reclamo',facility='CESFAM Padre Las Casas',category='Trato',source_area='Recepción',description='Solicitud de prueba acerca de orientación general de ingreso.'))
    assert r.status_code == 200, r.text[:150]
    folio = re.search(r'id="folio-text">([^<]+)', r.text).group(1)
    code = re.search(r'id="code-text">([^<]+)', r.text).group(1)
    return folio, code

def login(client,email):
    token = csrf(client, '/funcionarios/login')
    r = client.post('/funcionarios/login',data=dict(csrf_token=token,email=email,password='ClaveDePrueba2026!'))
    assert r.status_code == 200, r.text[:250]
    return r

def logout(client):
    token = csrf(client, '/funcionarios/panel')
    r = client.post('/funcionarios/salir',data=dict(csrf_token=token))
    assert r.status_code == 200

def test_home_and_logo(client):
    html = client.get('/').text
    assert 'Queremos' in html and 'logo_salud_municipal.jpg' in html
    assert client.get('/static/assets/logo_salud_municipal.jpg').status_code == 200

def test_public_registration_persists_and_private_tracking(client):
    folio, code = create_case(client)
    with SessionLocal() as db:
        assert db.query(Case).filter_by(folio=folio).count()==1
        assert db.query(CaseEvent).count()==1
        assert code not in db.query(Case).filter_by(folio=folio).first().tracking_hmac
    token=csrf(client,'/seguimiento')
    r=client.post('/seguimiento',data=dict(csrf_token=token,folio=folio,tracking_code=code))
    assert r.status_code==200
    assert 'Solicitud encontrada' in r.text
    assert 'orientación general de ingreso' not in r.text
    assert 'Recibido' in r.text
    denied=client.post('/seguimiento',data=dict(csrf_token=token,folio=folio,tracking_code='INCORRECTO'))
    assert 'No encontramos' in denied.text

def test_cannot_register_without_csrf(client):
    client.get('/solicitud')
    r=client.post('/solicitud',data=dict(csrf_token='incorrecto',case_type='Reclamo'))
    assert r.status_code==403

def test_survey_persisted(client):
    r=client.post('/encuesta',data=dict(csrf_token=csrf(client,'/encuesta'),rating='5',facility='CESFAM Las Colinas',aspect='Atención'))
    assert r.status_code==200 and 'Gracias por tu opinión' in r.text
    with SessionLocal() as db:
        assert db.query(Survey).count()==1

def test_employee_login_and_case_scope(client):
    folio,_=create_case(client)
    with SessionLocal() as db:
        case=db.query(Case).filter_by(folio=folio).one()
        case_id=case.id
    login(client,'farmacia@prueba.local')
    assert folio not in client.get('/funcionarios/panel').text
    assert client.get(f'/funcionarios/casos/{case_id}').status_code==404
    logout(client)
    login(client,'mesa@prueba.local')
    assert folio in client.get('/funcionarios/panel').text
    detail=client.get(f'/funcionarios/casos/{case_id}')
    assert 'Solicitud de prueba' in detail.text
    with SessionLocal() as db:
        farmacia=db.query(Unit).filter_by(name='Farmacia').one()
    token=csrf(client,f'/funcionarios/casos/{case_id}')
    update=client.post(f'/funcionarios/casos/{case_id}/actualizar',data=dict(csrf_token=token,status='Derivado',unit_id=str(farmacia.id),note='Derivación de prueba'))
    assert update.status_code==200
    assert folio not in client.get('/funcionarios/panel').text
    with SessionLocal() as db:
        assert db.query(Case).filter_by(id=case_id).one().status=='Derivado'
        assert db.query(CaseEvent).filter_by(case_id=case_id).count()==2
    logout(client)
    login(client,'farmacia@prueba.local')
    assert folio in client.get('/funcionarios/panel').text
    assert client.get(f'/funcionarios/casos/{case_id}').status_code==200

def test_official_scope_enforced_in_post(client):
    folio,_=create_case(client)
    with SessionLocal() as db:
        case_id=db.query(Case).filter_by(folio=folio).one().id
    login(client,'farmacia@prueba.local')
    token=csrf(client,'/funcionarios/panel')
    r=client.post(f'/funcionarios/casos/{case_id}/actualizar',data=dict(csrf_token=token,status='Cerrado'))
    assert r.status_code==403

def test_jefatura_reads_but_cannot_edit(client):
    folio,_=create_case(client)
    with SessionLocal() as db:
        case_id=db.query(Case).filter_by(folio=folio).one().id
    login(client,'jefatura@prueba.local')
    r=client.get(f'/funcionarios/casos/{case_id}')
    assert r.status_code==200 and 'Tu rol permite consultar' in r.text
    token=csrf(client,f'/funcionarios/casos/{case_id}')
    assert client.post(f'/funcionarios/casos/{case_id}/actualizar',data=dict(csrf_token=token,status='Cerrado')).status_code==403

def test_admin_adds_unit_and_staff(client):
    login(client,'admin@prueba.local')
    unit=client.post('/funcionarios/unidades',data=dict(csrf_token=csrf(client,'/funcionarios/unidades'),name='Unidad de prueba',description='Equipo académico'))
    assert unit.status_code==200 and 'Unidad de prueba' in unit.text
    with SessionLocal() as db:
        newunit=db.query(Unit).filter_by(name='Unidad de prueba').one()
    staff=client.post('/funcionarios/equipo',data=dict(csrf_token=csrf(client,'/funcionarios/equipo'),name='Funcionario Nuevo',email='nuevo@prueba.local',password='ClaveSeguraDePrueba2026!',role='funcionario',unit_id=str(newunit.id)))
    assert staff.status_code==200 and 'Funcionario Nuevo' in staff.text

def test_admin_notice_published_publicly(client):
    login(client,'admin@prueba.local')
    r=client.post('/funcionarios/avisos',data=dict(csrf_token=csrf(client,'/funcionarios/avisos'),text='Aviso de ejemplo académico'))
    assert r.status_code==200
    assert 'Aviso de ejemplo académico' in client.get('/').text

def test_no_default_demo_password(client):
    token=csrf(client,'/funcionarios/login')
    r=client.post('/funcionarios/login',data=dict(csrf_token=token,email='admin@prueba.local',password='DEMO2026'))
    assert 'incorrectos' in r.text and '/funcionarios/panel' not in r.url.path
