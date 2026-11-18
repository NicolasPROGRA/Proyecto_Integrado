"""Funciones de protección y reglas de autorización. No sustituye auditoría profesional."""
import hashlib
import hmac
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from argon2 import PasswordHasher, exceptions
from fastapi import HTTPException
from .database import INSTANCE

password_hasher = PasswordHasher()

PASSWORD_POLICY_MESSAGE = (
    'La contraseña debe tener entre 12 y 200 caracteres e incluir '
    'al menos una mayúscula, una minúscula, un número y un símbolo (por ejemplo, ! o #).'
)

def valid_new_password(raw: str) -> bool:
    """Política de complejidad para contraseñas nuevas, sin afectar los inicios de sesión existentes."""
    return (
        12 <= len(raw) <= 200
        and any(char.isupper() for char in raw)
        and any(char.islower() for char in raw)
        and any(char.isdigit() for char in raw)
        and any(not char.isalnum() and not char.isspace() for char in raw)
    )

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

def _same_local_origin_alias(origin: str, request) -> bool:
    """localhost y 127.0.0.1 son alternativas locales del mismo servidor."""
    try:
        submitted = urlsplit(origin)
        served = urlsplit(f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}")
        loopback = {'localhost', '127.0.0.1', '::1'}
        default_port = 443 if served.scheme == 'https' else 80
        return (
            submitted.scheme == served.scheme
            and submitted.hostname in loopback
            and served.hostname in loopback
            and (submitted.port or default_port) == (served.port or default_port)
        )
    except ValueError:
        return False

def verify_csrf(request, submitted):
    csrf = request.session.get('csrf')
    if not csrf or not hmac.compare_digest(str(csrf), str(submitted)):
        raise HTTPException(403, 'Token de formulario inválido. Actualiza la página.')
    # CSRF_LOCAL_COMPAT_V2: el servidor de la demostración escucha solo en
    # loopback. Ahí basta con el token CSRF de sesión: proxies locales,
    # navegadores y extensiones pueden reconstruir Origin de forma distinta.
    # El control adicional de Origin/Fetch Metadata permanece para accesos
    # que no sean completamente locales.
    local_hosts = {'127.0.0.1', 'localhost', '::1'}
    if (request.client and request.client.host in local_hosts
            and request.url.hostname in local_hosts):
        return
    # Fetch Metadata es controlado por el navegador; una petición cross-site
    # se rechaza incluso cuando se presenta un token que coincide.
    fetch_site = request.headers.get('sec-fetch-site', '').lower()
    if fetch_site == 'cross-site':
        raise HTTPException(403, 'El formulario proviene de un sitio no autorizado.')

    # En Windows una app local puede presentarse como localhost o 127.0.0.1,
    # o tener un esquema/host reconstruido por un proxy. Se acepta la petición
    # que el navegador identifica como same-origin, conservando el token CSRF.
    origin = request.headers.get('origin')
    if origin:
        try:
            parsed = urlsplit(origin)
            valid_origin = (
                parsed.scheme in ('http', 'https') and parsed.hostname
                and not parsed.username and not parsed.password
                and not parsed.path and not parsed.query and not parsed.fragment
            )
        except ValueError:
            valid_origin = False
        if not valid_origin:
            raise HTTPException(403, 'El formulario proviene de un sitio no autorizado.')
        expected_origin = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
        trusted = {expected_origin}
        trusted.update(value.strip().rstrip('/') for value in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if value.strip())
        if origin not in trusted and not _same_local_origin_alias(origin, request) and fetch_site != 'same-origin':
            raise HTTPException(403, 'El formulario proviene de un sitio no autorizado.')

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
