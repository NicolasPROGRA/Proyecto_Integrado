"""Importar de forma opcional los datos de la antigua BD SQLite a PostgreSQL.

La fuente se abre en modo SOLO LECTURA. No se importa sobre un destino que ya
tenga actividad; nunca se borran ni reemplazan registros existentes.

python -m app.migrar_sqlite --source instance/salud_plc.sqlite3
python -m app.migrar_sqlite --source instance/salud_plc.sqlite3 --apply
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal, engine, init_database, catalog
from .models import (Audit, Case, CaseEvent, CaseStatus, Category, Channel,
                     RecordType, Role, Staff, Survey, SurveyQuestion, Unit)
from .security import new_folio, new_tracking_code, tracking_hash

LEGACY = {'units', 'staff', 'cases', 'case_events', 'surveys', 'notices'}


def timestamp(value):
    return datetime.fromisoformat(value) if value else None


def legacy_rows(connection, name):
    return list(connection.execute(f'SELECT * FROM {name} ORDER BY id'))


def migrate(source, apply):
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('Configura primero un destino PostgreSQL en .env.')
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(f'No existe la base origen: {source}')
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as old:
        old.row_factory = sqlite3.Row
        table_names = {row[0] for row in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not LEGACY <= table_names:
            raise RuntimeError('El archivo origen no corresponde a la versión antigua de seis tablas.')
        data = {name: legacy_rows(old, name) for name in LEGACY}
    counts = {name: len(rows) for name, rows in data.items()}
    print('Fuente SQLite (solo lectura):', source)
    print('Registros hallados:', counts)
    print('Destino PostgreSQL:', engine.url.database)
    print('IMPORTANTE: los códigos de seguimiento existentes requieren conservar')
    print('el archivo instance/session_secret.key del proyecto anterior.')
    if not apply:
        print('Simulación terminada sin modificaciones. Agrega --apply para importar.')
        return
    init_database()
    with SessionLocal.begin() as db:
        if any(db.scalar(select(model.id).limit(1)) for model in (Staff, Case, Survey, Audit)):
            raise RuntimeError('Destino con datos: importación cancelada para evitar duplicados.')
        units = {row.name: row for row in db.scalars(select(Unit))}
        unit_ids = {}
        for entry in data['units']:
            existing = units.get(entry['name'])
            if existing is None:
                existing = Unit(name=entry['name'], description=entry['description'] or '',
                                active=bool(entry['active']))
                db.add(existing)
                db.flush()
            unit_ids[entry['id']] = existing.id

        staff_ids = {}
        for entry in data['staff']:
            role = catalog(db, Role, 'code', entry['role'])
            staff = Staff(full_name=entry['full_name'], email=entry['email'],
                          password_hash=entry['password_hash'], role_id=role.id,
                          unit_id=unit_ids[entry['unit_id']],
                          active=bool(entry['active']),
                          created_at=timestamp(entry['created_at']))
            db.add(staff)
            db.flush()
            staff_ids[entry['id']] = staff.id

        web = catalog(db, Channel, 'name', 'Portal web')
        case_ids = {}
        for entry in data['cases']:
            kind = catalog(db, RecordType, 'name', entry['case_type'])
            category = catalog(db, Category, 'name', entry['category'])
            status = catalog(db, CaseStatus, 'name', entry['status'])
            case = Case(folio=entry['folio'], tracking_hmac=entry['tracking_hmac'],
                        record_type_id=kind.id, channel_id=web.id,
                        category_id=category.id, status_id=status.id,
                        unit_id=unit_ids[entry['unit_id']], facility=entry['facility'],
                        source_area=entry['source_area'], description=entry['description'],
                        created_at=timestamp(entry['created_at']),
                        updated_at=timestamp(entry['updated_at']))
            db.add(case)
            db.flush()
            case_ids[entry['id']] = case.id
            db.add(Audit(record_id=case.id, event_type='registro_importado',
                         details={'origen': 'SQLite ES3 anterior'}))

        for entry in data['case_events']:
            db.add(CaseEvent(case_id=case_ids[entry['case_id']],
                             actor_id=staff_ids.get(entry['actor_id']), action=entry['action'],
                             note=entry['note'] or '', created_at=timestamp(entry['created_at'])))
        question = catalog(db, SurveyQuestion, 'code', 'SAT_GENERAL')
        kind_survey = catalog(db, RecordType, 'name', 'Encuesta')
        for entry in data['surveys']:
            category = catalog(db, Category, 'name', entry['aspect'])
            record = Case(folio=new_folio(), tracking_hmac=tracking_hash(new_tracking_code()),
                          record_type_id=kind_survey.id, channel_id=web.id,
                          category_id=category.id, facility=entry['facility'],
                          source_area='Encuesta importada',
                          created_at=timestamp(entry['created_at']),
                          updated_at=timestamp(entry['created_at']))
            db.add(record)
            db.flush()
            db.add(Survey(record_id=record.id, question_id=question.id, rating=entry['rating'],
                          created_at=timestamp(entry['created_at'])))
        for entry in data['notices']:
            db.add(Audit(actor_id=staff_ids.get(entry['editor_id']),
                         event_type='public_notice', details={'text': entry['text'] or ''},
                         created_at=timestamp(entry['updated_at'])))
    print('Importación completa. La fuente SQLite no se modificó.')


def main():
    parser = argparse.ArgumentParser(description='Migración controlada desde SQLite anterior')
    parser.add_argument('--source', required=True, help='Ruta del archivo SQLite de la versión anterior')
    parser.add_argument('--apply', action='store_true', help='Confirmar escritura sobre PostgreSQL vacío')
    options = parser.parse_args()
    try:
        migrate(options.source, options.apply)
    except (RuntimeError, FileNotFoundError, sqlite3.Error, ValueError, KeyError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
