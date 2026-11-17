"""Configuración y catálogo inicial del esquema ES3 de 14 tablas."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / 'instance'
INSTANCE.mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT / '.env')
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///' + str(INSTANCE / 'salud_plc.sqlite3'))
if DB_URL.startswith('postgresql://'):
    DB_URL = DB_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
connect_args = {'check_same_thread': False} if DB_URL.startswith('sqlite:') else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
if DB_URL.startswith('sqlite:'):
    # SQLite desactiva las claves foráneas de forma predeterminada.
    @event.listens_for(engine, 'connect')
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def init_database():
    from . import models
    Base.metadata.create_all(bind=engine)
    # create_all no altera esquemas anteriores: usar una BD ES3 nueva o el
    # migrador documentado, nunca borrar datos de una BD de trabajo.
    from .security import ROLES
    with SessionLocal() as db:
        seeds = [
            (models.Role, [{'code': k, 'label': v} for k, v in ROLES.items()]),
            (models.Unit, [
                {'name': 'Mesa de entrada', 'description': 'Recepción y clasificación de solicitudes'},
                {'name': 'Atención usuaria', 'description': 'Orientación y atención de casos'},
                {'name': 'Farmacia', 'description': 'Casos relacionados con farmacia'},
                {'name': 'Calidad', 'description': 'Seguimiento y mejora continua'},
                {'name': 'Dirección', 'description': 'Supervisión institucional'},
                {'name': 'Comunicaciones', 'description': 'Contenidos públicos'},
            ]),
            (models.RecordType, [{'name': x} for x in ('Reclamo', 'Sugerencia', 'Agradecimiento', 'Encuesta')]),
            (models.Channel, [{'name': 'Portal web'}]),
            (models.Category, [{'name': x} for x in ('Atención', 'Trato', 'Información', 'Accesibilidad', 'Tiempos de espera', 'Farmacia', 'Otro')]),
            (models.CaseStatus, [{'name': x} for x in ('Recibido', 'En proceso', 'Derivado', 'Cerrado')]),
            (models.SurveyQuestion, [{'code': 'SAT_GENERAL', 'text': '¿Cómo evalúa la atención recibida?'}]),
        ]
        for model, values in seeds:
            if not db.scalar(select(model.id).limit(1)):
                db.add_all(model(**value) for value in values)
        db.commit()


def catalog(db, model, key, value):
    item = db.scalar(select(model).where(getattr(model, key) == value))
    if item is None:
        raise LookupError(f'Falta el catálogo {model.__tablename__}: {value}')
    return item

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
