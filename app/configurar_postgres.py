"""Asistente local: prueba PostgreSQL y guarda la conexión en .env.

La clave se solicita mediante getpass: no se imprime ni se comparte.
Ejecutar: python -m app.configurar_postgres
"""
import getpass
import re
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL
from dotenv import set_key


ROOT = Path(__file__).resolve().parent.parent


def prompt(label, default):
    return input(f'{label} [{default}]: ').strip() or default


def main():
    print('Configuración de PostgreSQL para Salud Municipal ES3')
    print('La contraseña no aparecerá en pantalla. No envíes este archivo .env a GitHub.')
    host = prompt('Servidor', 'localhost')
    port_str = prompt('Puerto', '5432')
    user = prompt('Usuario de PostgreSQL', 'postgres')
    database = prompt('Base de datos del proyecto', 'salud_plc_es3')
    if not port_str.isdecimal() or not 1 <= int(port_str) <= 65535:
        print('Puerto inválido.')
        return 1
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,62}', database):
        print('Usa un nombre de base de datos sin espacios ni guiones.')
        return 1
    password = getpass.getpass('Contraseña local de PostgreSQL: ')
    if not password:
        print('Debes indicar la contraseña configurada durante la instalación.')
        return 1
    options = dict(host=host, port=int(port_str), user=user, password=password, connect_timeout=5)
    try:
        with psycopg.connect(dbname=database, **options) as connection:
            connection.execute('SELECT 1').fetchone()
    except psycopg.errors.InvalidCatalogName:
        answer = input(f'No existe {database}. ¿Crear esa base de datos nueva? [s/N]: ').strip().lower()
        if answer not in ('s', 'si', 'sí'):
            print('Puedes crearla en pgAdmin y ejecutar de nuevo este configurador.')
            return 1
        try:
            with psycopg.connect(dbname='postgres', autocommit=True, **options) as maintenance:
                maintenance.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            with psycopg.connect(dbname=database, **options) as connection:
                connection.execute('SELECT 1').fetchone()
        except psycopg.Error as exc:
            print(f'No fue posible crear o conectar la base: {exc.__class__.__name__}.')
            print('Crea la base manualmente desde pgAdmin y vuelve a intentar.')
            return 1
    except psycopg.Error as exc:
        print(f'No se pudo conectar: {exc.__class__.__name__}.')
        print('Revisa servicio PostgreSQL, servidor, puerto, usuario y contraseña.')
        return 1
    url = URL.create(
        'postgresql+psycopg', username=user, password=password,
        host=host, port=int(port_str), database=database,
    ).render_as_string(hide_password=False)
    env_file = ROOT / '.env'
    set_key(str(env_file), 'DATABASE_URL', url, quote_mode='always')
    print(f'Conexión comprobada con {database}. Configuración guardada localmente.')
    print('Ahora ejecuta INICIAR_WINDOWS.bat y CREAR_ADMIN_WINDOWS.bat.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
