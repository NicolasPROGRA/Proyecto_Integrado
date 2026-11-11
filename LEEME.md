# Salud Municipal Padre Las Casas — versión 0.1

**Primera etapa real de programación** a partir del prototipo HTML aprobado. Conserva el logotipo original que compartiste y utiliza un servidor **FastAPI + SQLAlchemy** con **SQLite local**. Preparado para conexión futura con PostgreSQL por variable de entorno.

> **Importante:** Es un proyecto académico en desarrollo, no un servicio municipal en producción. Utiliza exclusivamente información ficticia. No registrar datos de pacientes, RUT, diagnósticos ni información de salud real en esta etapa.

## 1. Instalación en Windows con Visual Studio Code

1. Descomprime el archivo ZIP, abre la carpeta `Salud_PLC_Backend_01` en VS Code.
2. Abre una terminal en esa carpeta y ejecuta:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

3. Crea **tu primera cuenta administradora**, con una contraseña elegida por ti (al menos 12 caracteres):

```powershell
python -m app.crear_admin
```

4. Inicia el servidor:

```powershell
python -m uvicorn app.main:app --reload
```

5. Abre `http://127.0.0.1:8000` en el navegador. Para funcionarios, entra a `http://127.0.0.1:8000/funcionarios/login` con la cuenta creada.

> Si el comando `py` no está disponible, usa `python -m venv .venv`. Si PowerShell impide la activación, puedes ejecutar sin activar usando `.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.venv\Scripts\python.exe -m app.crear_admin` y `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

## 2. Qué puedes hacer ya

**Público (sin iniciar sesión):**
- Inicio con diseño y logo del Departamento de Salud Municipal.
- Registrar reclamo, sugerencia o agradecimiento en la base de datos.
- Recibir un **folio** y un **código privado** (solo se muestran una vez).
- Consultar el estado del folio sin revelar contenido interno.
- Responder encuesta de satisfacción anónima.

**Funcionarios (con cuentas reales):**
- Iniciar/cerrar sesión con contraseña protegida mediante Argon2.
- Ver los casos de su unidad según perfil.
- Gestionar estados y registrar un historial de seguimiento.
- Derivar casos entre áreas cuando el perfil lo permite.
- Consultar reportes resumidos.
- Como administrador: gestionar unidades y dar de alta cuentas.
- Como administrador o editor de contenidos: publicar avisos informativos.

**Roles actuales:** `recepcion`, `funcionario`, `encargado`, `jefatura`, `admin`, `contenidos`.

## 3. Cómo probar el recorrido completo

1. Registra un reclamo desde el inicio con datos **inventados**.
2. Guarda el folio y el código privado de la pantalla de confirmación.
3. Consulta su estado en «Seguimiento».
4. Entra como administrador y abre el caso desde el panel.
5. Cambia su estado, escribe una observación y deriva a Farmacia.
6. Crea un usuario de Farmacia en «Equipo» y entra con esa cuenta.
7. Revisa que el caso derivado esté en la bandeja de Farmacia.
8. Regresa al portal público y verifica que el estado cambió.

## 4. Base de datos

- Se crea automáticamente en `instance/salud_plc.sqlite3` y **conserva los registros** después de cerrar el servidor.
- Contiene tablas de `units`, `staff`, `cases`, `case_events`, `surveys`, `notices`.
- Este es un **MVP inicial**, no la implementación definitiva de las 14 tablas del modelo ER académico. Esas se incorporarán con migraciones durante las siguientes etapas.
- Para conectar PostgreSQL más adelante: instala `psycopg[binary]` y define `DATABASE_URL=postgresql+psycopg://...`, con credenciales privadas y almacenamiento seguro.
- **No ejecutes el script PostgreSQL anterior sobre esta base sin adaptar primero los modelos.**

## 5. Pruebas automatizadas

Instala el entorno de pruebas si no lo tienes:

```powershell
python -m pip install pytest httpx
python -m pytest -q
```

Las pruebas abarcan registro, privacidad del seguimiento, encuesta, login, control de accesos, derivación de unidad, historial, altas administrativas y avisos.

## 6. Seguridad y limitaciones

- Contraseñas cifradas con Argon2; no hay cuenta de demostración ni contraseña publicada.
- La sesión usa una cookie firmada `HttpOnly` y `SameSite=Lax`; se puede exigir HTTPS al activar `COOKIE_SECURE=1`.
- Los formularios se validan en el servidor y llevan protección CSRF.
- El código privado de seguimiento se guarda como HMAC, no en texto plano.
- Los permisos de cada área se verifican en la **base de datos y las rutas**, no solo ocultando botones.
- Hay un límite de intentos sencillo en memoria, apropiado solamente para **desarrollo local**.
- Para uso institucional real se requieren: HTTPS, revisión de seguridad profesional, políticas de privacidad/retención, respaldos protegidos, registro de auditoría ampliado, migraciones controladas, monitoreo, procedimientos OIRS validados, confirmación de roles y establecimiento, mecanismos de recuperación de contraseñas, protección antiabuso robusta e infraestructura municipal autorizada.

## 7. Archivos importantes

| Archivo | Función |
|---|---|
| `app/main.py` | Rutas, reglas y acciones del servidor |
| `app/models.py` | Tablas de datos |
| `app/database.py` | Conexión y creación inicial de BD |
| `app/security.py` | Contraseñas, sesiones, CSRF y permisos |
| `app/crear_admin.py` | Crear administrador sin clave por defecto |
| `app/templates/` | Pantallas HTML conectadas al backend |
| `app/static/` | CSS, JavaScript y logo real |
| `tests/` | Pruebas automatizadas |

**Siguiente etapa sugerida:** migraciones para expandir el ER, filtros y asignaciones de casos, mejoras de permisos detallados, notificaciones y PostgreSQL en entorno de pruebas.


## Corrección de instalación para Python 3.15 (08-11-2026)

- Se cambió `uvicorn[standard]` por `uvicorn` para evitar la instalación de PyYAML y otros extras no requeridos.
- Se incluyó `pydantic>=2.14,<3.0`, con soporte de Python 3.15.
- `INICIAR_WINDOWS.bat` verifica e instala las dependencias **aunque ya exista** `.venv`. Esto resuelve el caso de instalación interrumpida.
- No necesitas instalar Visual C++ por el error de PyYAML si la instalación básica resuelve correctamente.
- No se garantiza compatibilidad completa de todos los paquetes con Python 3.15 en cada equipo; si aparece otro error, conserva el registro para identificarlo.

### Cuando ya tienes la carpeta en VS Code
Puedes modificar `requirements.txt` y reemplazar `INICIAR_WINDOWS.bat` por los archivos de esta versión, sin tocar tu base de datos `instance/`. Después ejecuta en PowerShell:

```powershell
.\INICIAR_WINDOWS.bat
```

Para comprobar la versión del entorno virtual:

```powershell
.\.venv\Scripts\python.exe --version
```

**Advertencia:** proyecto local de desarrollo; no usar datos reales de pacientes.
