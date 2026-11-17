# Salud Municipal Padre Las Casas — Proyecto Integrado ES3

Este archivo fue actualizado para reemplazar las instrucciones antiguas del prototipo SQLite. La **guía principal vigente** es [README.md](README.md). El código ES3 usa 14 tablas, conexión PostgreSQL con Psycopg 3 y el portal FastAPI; la base SQLite solamente se usa en pruebas automáticas y como alternativa explícita de desarrollo.

## Instalación rápida con PostgreSQL 18 en Windows

3. Ejecuta `CONFIGURAR_POSTGRESQL_WINDOWS.bat`; selecciona la base `salud_plc_es3` y verifica la conexión con el PostgreSQL.
4. Ejecuta `INICIAR_WINDOWS.bat`; el programa valida el esquema de 14 tablas y arranca el servidor local.
5. Si no creaste una cuenta administrativa, ejecuta `CREAR_ADMIN_WINDOWS.bat` y elige una contraseña de al menos 12 caracteres.
6. Abre <http://127.0.0.1:8000> para el portal o <http://127.0.0.1:8000/funcionarios/login> para Gestión.

Si PowerShell impide la activación de scripts, **no necesitas cambiar su política**: los archivos `.bat` del proyecto usan directamente el ejecutable Python de `.venv`.

## Qué funciones se implementaron

- **Público:** reclamo, sugerencia, agradecimiento, encuesta anónima y seguimiento privado por folio/código.
- **Gestión:** clasificación, derivación, estados e historial, filtros y paginación por unidad y rol, adjuntos privados y estadísticas.
- **Reportes:** filtros por fecha inicial/final (ambas inclusive), categoría y tipo; resultados limitados al alcance del perfil.
- **Administración:** usuarios, unidades, categorías (crear/activar/desactivar) y avisos. «Otro» siempre permanece activa y los casos históricos no se eliminan.
- **Seguridad:** mensajes de error dentro de los formularios, autorización comprobada en el servidor, protección CSRF y de origen, revocación de sesiones cerradas, caducidad por inactividad, auditoría de accesos y cabeceras de seguridad del navegador.

## Evaluación y límites

El 17/11/2026 se ejecutaron **50 pruebas automáticas aprobadas** sobre una SQLite temporal aislada; el equipo mostró capturas de conexión a PostgreSQL 18 con 14 tablas. Antes de entregar, falta comprobar en el equipo Windows un ingreso, una actualización y una consulta SQL real, además del botón Atrás/Adelante tras cerrar sesión. Ver [ES3_DEMOSTRACION.md](ES3_DEMOSTRACION.md) y [ES3_POSTGRESQL.md](ES3_POSTGRESQL.md).

Este sistema es un **piloto académico local**. Los tótems, Rayen, WordPress institucional, el despliegue real, la revisión profesional de accesibilidad y seguridad y la validación con usuarios municipales requieren autorización y recursos externos. No registrar información clínica ni datos personales reales.
