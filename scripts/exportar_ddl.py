"""Exporta el DDL PostgreSQL a partir de los mismos modelos que usa la app."""
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
from app import models  # noqa: F401 - registra las 14 entidades


def main():
    dialect = postgresql.dialect()
    statements = [
        '-- Esquema PostgreSQL ES3 / Salud Municipal Padre Las Casas',
        '-- Generado desde app/models.py. Crear antes una base vacía con pgAdmin.',
        '-- La aplicación también puede crear el esquema mediante SQLAlchemy.',
    ]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ';')
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ';')
    path = Path(__file__).resolve().parent.parent / 'evidencias' / 'esquema_postgresql_es3.sql'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n\n'.join(statements) + '\n', encoding='utf-8')
    print(f'{len(Base.metadata.tables)} tablas y sus índices exportados a {path}')


if __name__ == '__main__':
    main()
