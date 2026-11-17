"""Validación reproducible de PostgreSQL, esquema y catálogos."""
from sqlalchemy import inspect, text

from .database import engine, init_database


EXPECTED = {
    'rol', 'unidad', 'usuario_admin', 'tipo_registro', 'canal', 'categoria',
    'estado_caso', 'ciudadano', 'registro', 'seguimiento', 'pregunta_encuesta',
    'respuesta_encuesta', 'adjunto', 'auditoria',
}


def main():
    if engine.dialect.name != 'postgresql':
        print('ERROR: DATABASE_URL no apunta a PostgreSQL.')
        print('Ejecuta CONFIGURAR_POSTGRESQL_WINDOWS.bat primero.')
        return 1
    try:
        init_database()
        with engine.connect() as connection:
            connection.execute(text('SELECT 1')).scalar_one()
        inspector = inspect(engine)
        found = set(inspector.get_table_names(schema='public'))
    except Exception as exc:
        print(f'ERROR de conexión o esquema PostgreSQL: {exc.__class__.__name__}')
        print('Revisa que PostgreSQL esté iniciado y que .env tenga la conexión correcta.')
        return 1
    missing = EXPECTED - found
    if missing:
        print('ERROR: faltan tablas: ' + ', '.join(sorted(missing)))
        return 1
    registro_refs = {fk['referred_table'] for fk in inspector.get_foreign_keys('registro', schema='public')}
    encuesta_refs = {fk['referred_table'] for fk in inspector.get_foreign_keys('respuesta_encuesta', schema='public')}
    if not {'tipo_registro', 'canal', 'categoria', 'estado_caso', 'unidad'} <= registro_refs:
        print('ERROR: faltan relaciones esenciales de registro.')
        return 1
    if encuesta_refs != {'registro', 'pregunta_encuesta'}:
        print('ERROR: la respuesta de encuesta no tiene las FK esperadas.')
        return 1
    print(f'PostgreSQL correcto: BD {engine.url.database}, 14 tablas y relaciones verificadas.')
    if len(found) != len(EXPECTED):
        print(f'Nota: el esquema public contiene {len(found)} tablas en total.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
