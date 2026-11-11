"""Base de datos local en desarrollo y compatible con PostgreSQL por configuración."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / 'instance'
INSTANCE.mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///' + str(INSTANCE / 'salud_plc.sqlite3'))
connect_args = {'check_same_thread': False} if DB_URL.startswith('sqlite:') else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def init_database():
    from . import models
    Base.metadata.create_all(bind=engine)
    from .models import Unit
    with SessionLocal() as db:
        if db.query(Unit).count() == 0:
            db.add_all([
                Unit(name='Mesa de entrada', description='Recepción y clasificación de solicitudes'),
                Unit(name='Atención usuaria', description='Orientación y atención de casos'),
                Unit(name='Farmacia', description='Casos relacionados con farmacia'),
                Unit(name='Calidad', description='Seguimiento y mejora continua'),
                Unit(name='Dirección', description='Supervisión institucional'),
                Unit(name='Comunicaciones', description='Contenidos públicos'),
            ])
            db.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
