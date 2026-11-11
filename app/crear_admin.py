"""Crear el primer usuario administrador desde consola (sin contraseña predefinida).

Ejemplo: python -m app.crear_admin
"""
import getpass
from sqlalchemy import select
from .database import init_database, SessionLocal
from .models import Unit, Staff
from .security import hash_password

def main():
    init_database()
    print('Crear administrador del entorno local de desarrollo')
    name = input('Nombre completo: ').strip()
    email = input('Correo electrónico: ').strip().lower()
    password = getpass.getpass('Contraseña (mínimo 12 caracteres): ')
    confirm = getpass.getpass('Repetir contraseña: ')
    if len(name) < 3 or '@' not in email or len(password) < 12 or password != confirm:
        print('Datos inválidos o contraseñas distintas. No se creó la cuenta.')
        return
    with SessionLocal() as db:
        if db.scalar(select(Staff).where(Staff.email == email)):
            print('Ese correo ya tiene una cuenta.')
            return
        unit = db.scalar(select(Unit).where(Unit.name == 'Dirección'))
        if not unit:
            print('No existe la unidad Dirección')
            return
        db.add(Staff(full_name=name, email=email, password_hash=hash_password(password), role='admin', unit_id=unit.id, active=True))
        db.commit()
    print('Cuenta administradora creada. Ingresa en /funcionarios/login')

if __name__ == '__main__':
    main()
