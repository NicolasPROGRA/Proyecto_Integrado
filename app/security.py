"""Funciones de protección y reglas de autorización. No sustituye auditoría profesional."""
import hashlib
import hmac
import secrets
from pathlib import Path
from argon2 import PasswordHasher, exceptions
from fastapi import HTTPException
from .database import INSTANCE

password_hasher = PasswordHasher()

def session_secret():
    import os
    val = os.getenv('SESSION_SECRET')
    if val and len(val) >= 32:
        return val
    path = INSTANCE / 'session_secret.key'
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding='utf-8')
        try: path.chmod(0o600)
        except OSError: pass
    return path.read_text(encoding='utf-8')

APP_SECRET = session_secret()

def hash_password(raw: str):
    return password_hasher.hash(raw)

def verify_password(stored: str, raw: str):
    try:
        return password_hasher.verify(stored, raw)
    except (exceptions.VerifyMismatchError, exceptions.VerificationError, exceptions.InvalidHashError):
        return False

def new_folio():
    return 'PLC-' + secrets.token_hex(6).upper()

def new_tracking_code():
    return secrets.token_urlsafe(18)

def tracking_hash(code: str):
    return hmac.new(APP_SECRET.encode(), code.encode(), hashlib.sha256).hexdigest()

def check_tracking(expected: str, candidate: str):
    return hmac.compare_digest(expected, tracking_hash(candidate))

def csrf_for(request):
    if 'csrf' not in request.session:
        request.session['csrf'] = secrets.token_urlsafe(32)
    return request.session['csrf']

def verify_csrf(request, submitted):
    csrf = request.session.get('csrf')
    if not csrf or not hmac.compare_digest(str(csrf), str(submitted)):
        raise HTTPException(403, 'Token de formulario inválido. Actualiza la página.')

ROLES = {
    'recepcion': 'Recepción',
    'funcionario': 'Funcionario de unidad',
    'encargado': 'Encargado de unidad',
    'jefatura': 'Jefatura',
    'admin': 'Administración general',
    'contenidos': 'Editor de contenidos',
}

def can_view_case(staff, case):
    return staff.role in ('admin', 'jefatura') or (
        staff.role in ('recepcion', 'funcionario', 'encargado') and staff.unit_id == case.unit_id
    )

def can_edit_case(staff, case):
    return staff.role in ('admin', 'recepcion', 'funcionario', 'encargado') and can_view_case(staff, case)

def can_reassign(staff):
    return staff.role in ('admin', 'recepcion')
