# Proyecto Integrado ES3 — Salud Municipal Padre Las Casas

Aplicación académica para registrar y gestionar satisfacción usuaria, reclamos, sugerencias y agradecimientos. Utiliza **PostgreSQL y el modelo relacional de 14 tablas definido en la ES2**, con FastAPI y SQLAlchemy en el servidor web. Incluye portal ciudadano, seguimiento por código privado, adjuntos privados, contactos voluntarios y panel por roles.

## Iniciar con PostgreSQL en Windows

1. Tener **PostgreSQL 14 o superior** funcionando en Windows y Python **3.12 o 3.13** instalado.
2. Ejecutar **`CONFIGURAR_POSTGRESQL_WINDOWS.bat`**. Indicar usuario y contraseña de PostgreSQL; la clave se solicita sin mostrarse. El configurador permite crear una base nueva `salud_plc_es3` con confirmación si el usuario tiene permiso.
3. Ejecutar **`INICIAR_WINDOWS.bat`**. El programa verifica PostgreSQL, crea las 14 tablas y carga los catálogos al iniciar.
4. Ejecutar **`CREAR_ADMIN_WINDOWS.bat`** en otra ventana para crear el primer administrador (clave de al menos 12 caracteres).
5. Abrir <http://127.0.0.1:8000>. El panel interno está en <http://127.0.0.1:8000/funcionarios/login>.

El archivo local `.env` contiene la URL de conexión; **no se debe compartir ni subir a GitHub**. El configurador no envía la contraseña a este chat.

## Iniciar desde terminal

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
# Configura una vez la conexión a PostgreSQL:
python -m app.configurar_postgres
python -m app.verificar_postgres
python -m app.crear_admin
python -m uvicorn app.main:app --reload
```

## Pruebas y evidencias de la ES3

```bash
python -m pip install pytest httpx
python -m pytest -q --junitxml=evidencias/resultado_pruebas_es3.xml
python -m scripts.exportar_ddl
python -m scripts.generar_diagrama_bd
```

**50 pruebas aprobadas localmente el 17/11/2026.** Las pruebas automatizadas usan una SQLite temporal aislada para no alterar tu PostgreSQL. Se valida la compilación del DDL PostgreSQL, el modelo normalizado, los formularios, los reportes filtrados, la administración del catálogo, el control de acceso y el cierre de sesión. El equipo mostró capturas de PostgreSQL 18 conectado con 14 tablas, pero aún debe evidenciar un caso creado, derivado y consultado en su propia base real.

### Informes y categorías (requisitos de ES1 y ES2)

- En **Gestión → Reportes**, selecciona fecha inicial, fecha final, categoría y/o tipo de solicitud; ambos extremos del período se incluyen. La pantalla indica cuántos casos cumplen los filtros. Cada perfil ve únicamente sus unidades autorizadas; administración y jefatura también pueden consultar indicadores de encuestas anónimas.
- En **Gestión → Categorías** (solo administración), crea nuevos motivos o desactiva los existentes. Los formularios públicos muestran solo los motivos activos; los históricos permanecen para los reportes y el seguimiento. La opción **Otro** no se puede desactivar.
- Esas operaciones están cubiertas por `tests/test_es1_es2_requirements.py`. La correspondencia entre historias HU-01 a HU-08 y el código se documenta en [ES3_IMPLEMENTACION.md](ES3_IMPLEMENTACION.md).

### Validación de formularios

- Si el usuario agrega un nombre o correo de contacto en **Compartir experiencia**, debe ingresar un correo válido y marcar el consentimiento antes de continuar. El aviso aparece en rojo dentro del formulario, sin cambiar de página.
- Los campos obligatorios, selección de encuesta, longitudes y adjuntos mayores de 2 MB muestran errores antes del envío cuando JavaScript está disponible.
- El servidor vuelve a validar la información. Si se detecta un error de solicitud o encuesta, muestra la explicación dentro del formulario y conserva los datos escritos (excepto archivos y claves privadas). Otros errores HTTP se muestran con el diseño institucional, no como una pantalla de JSON.
- Si ya tenías el sistema abierto antes de actualizar, reinicia `INICIAR_WINDOWS.bat` y recarga la página con `Ctrl + F5`.

### Seguridad al cerrar sesión

- Al cerrar sesión desde Gestión, se eliminan los datos de sesión del navegador y se abre el formulario de acceso con una confirmación visible.
- Cada inicio de sesión recibe un identificador aleatorio vinculado a la auditoría. Al salir, ese identificador queda revocado en la base de datos; **una copia antigua de la cookie ya no permite volver a entrar**. La sesión también caduca tras **30 minutos sin actividad**, además de la duración máxima de la cookie.
- Los intentos fallidos de acceso quedan auditados sin almacenar la contraseña ingresada.
- Los formularios verifican el token CSRF y rechazan peticiones originadas en otros sitios. Solo si existe un proxy con un dominio público autorizado se debe configurar `CSRF_TRUSTED_ORIGINS` con esa URL; para uso local no es necesario.
- Se agregaron `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` y `Permissions-Policy`. La cookie puede usar `Secure` al publicar exclusivamente mediante HTTPS (`COOKIE_SECURE=1`).
- Las respuestas del área de funcionarios llevan `Cache-Control: private, no-store, no-cache, max-age=0, must-revalidate` y encabezados compatibles para evitar la reutilización de pantallas privadas desde caché.
- Ante una navegación Atrás/Adelante, la interfaz oculta el panel anterior y consulta `/funcionarios/sesion-actual` al servidor. Sin sesión vigente redirige a `/funcionarios/login?sesion=finalizada`, mostrando el aviso «No puedes ingresar a Gestión porque tu sesión está cerrada. Vuelve a iniciar sesión.»
- El servidor siempre verifica la sesión y los permisos en cada ruta; las medidas visuales complementan esos controles. Prueba manual recomendada en Chrome/Edge: iniciar sesión, abrir panel, cerrar sesión, utilizar Atrás y Adelante, y confirmar que no se vuelve a mostrar ningún caso hasta autenticarse nuevamente.

### Textos de la interfaz

Las pantallas públicas y el acceso de funcionarios tienen textos de atención usuaria. Se retiraron los avisos visibles sobre «entorno académico», «datos ficticios» y «base de datos local de pruebas»; las advertencias normales de privacidad, consentimiento y protección del código de seguimiento se mantienen. La condición de piloto académico y sus límites de seguridad **continúan documentados aquí** y en el informe, y no debe confundirse el nuevo aspecto visual con una autorización para usar datos reales de pacientes.

## Si tenías datos en la versión antigua de SQLite

La base PostgreSQL nueva comienza sin reclamos históricos. Para preservar datos anteriores, hay un migrador opcional que **lee SQLite sin modificarlo** y solo importa a un PostgreSQL sin actividad:

```bash
python -m app.migrar_sqlite --source instance/salud_plc.sqlite3
python -m app.migrar_sqlite --source instance/salud_plc.sqlite3 --apply
```

Si tienes datos históricos, realiza esta importación **después de configurar PostgreSQL y antes de crear el administrador o registrar nuevos casos**. Conserva también `instance/session_secret.key` si necesitas que funcionen los códigos privados de seguimiento antiguos. Haz una copia de seguridad de ambas bases antes de la migración.

- [Guía de implementación y evidencias ES3](ES3_IMPLEMENTACION.md)
- [Guion para demostración de 10 minutos](ES3_DEMOSTRACION.md)
- [Esquema SQL PostgreSQL](evidencias/esquema_postgresql_es3.sql) y [diagrama de 14 entidades](evidencias/modelo_14_entidades_es3.png)
- [Pruebas originales](tests/test_workflow.py), [nuevas pruebas ES3](tests/test_es3.py) y [pruebas de modelo](tests/test_es3_modelo.py)
- [Pruebas de requisitos ES1 y ES2](tests/test_es1_es2_requirements.py)
- [Pruebas adicionales de seguridad](tests/test_security_hardening.py)

**Alcance:** piloto académico local sin datos reales. Las 14 tablas y la integración aplicativa con PostgreSQL están implementadas en código; la validación contra el servidor PostgreSQL del equipo expositor es el paso pendiente y obligatorio antes de presentar. La integración institucional con WordPress/Rayen, despliegue real, validación con usuarios y auditorías de seguridad profesionales están fuera de esta ES3. No utilizar como servicio municipal en producción.

**Al actualizar desde otro ZIP:** primero respalda tu carpeta anterior. Conserva sus archivos locales `.env`, `instance/session_secret.key` y `instance/private_uploads` sin sobrescribirlos. Descomprime esta versión en una nueva carpeta, copia solo los archivos de configuración y privados que correspondan, ejecuta `INICIAR_WINDOWS.bat` y recarga el navegador con `Ctrl + F5`. **El ZIP no modifica por sí solo el proyecto que ya tienes descargado ni el repositorio GitHub.**
