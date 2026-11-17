"""Genera el diagrama del esquema implementado a partir de SQLAlchemy."""
import subprocess
from pathlib import Path

from app.database import Base
from app import models  # noqa: F401


def main():
    evidence = Path(__file__).resolve().parent.parent / 'evidencias'
    evidence.mkdir(parents=True, exist_ok=True)
    dot_path = evidence / 'modelo_14_entidades_es3.dot'
    image_path = evidence / 'modelo_14_entidades_es3.png'
    lines = [
        'digraph ModeloES3 {',
        '  graph [rankdir=LR, bgcolor="white", nodesep=0.26, ranksep=1.1, splines=polyline];',
        '  node [shape=record, fontname="DejaVu Sans", fontsize=10, color="#337e7a", style=filled, fillcolor="#e6f5f2"];',
        '  edge [color="#5f797b", arrowsize=0.65, penwidth=1.1];',
    ]
    for table in Base.metadata.sorted_tables:
        fields = []
        for column in table.columns:
            suffix = ' PK' if column.primary_key else (' FK' if column.foreign_keys else '')
            fields.append(column.name + suffix)
        # No omitir entidades ni llaves; limitar columnas informativas para legibilidad.
        visible = fields[:7]
        if len(fields) > 7:
            visible.append(f'... {len(fields) - 7} más')
        label = '{' + table.name.upper() + '|' + r'\l'.join(visible) + r'\l' + '}'
        lines.append(f'  "{table.name}" [label="{label}"];')
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            target = fk.column.table.name
            lines.append(f'  "{table.name}" -> "{target}" [label="{fk.parent.name}", fontsize=8];')
    lines.append('}')
    dot_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    try:
        subprocess.run(['dot', '-Tpng', '-Gdpi=180', str(dot_path), '-o', str(image_path)], check=True)
        print(f'Diagrama generado con {len(Base.metadata.tables)} tablas: {image_path}')
    except FileNotFoundError:
        print('Graphviz no disponible; se generó la fuente DOT.')


if __name__ == '__main__':
    main()
