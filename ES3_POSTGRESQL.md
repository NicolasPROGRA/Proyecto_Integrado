# Instalación PostgreSQL y evidencias de la Evaluación Sumativa 3

Esta guía sirve para **comprobar en tu Windows** lo que está implementado en el código. No envíes contraseñas ni capturas con credenciales. Usa solamente registros ficticios de prueba.

## Paso 1. Preparar PostgreSQL

1. Abre **pgAdmin 4** o los servicios de Windows y comprueba que PostgreSQL se encuentre iniciado.
2. Ten presente la contraseña del usuario que creaste al instalar PostgreSQL (normalmente `postgres`).
3. Descomprime el proyecto completo en una carpeta local, sin mezclarlo con una base de datos antigua.
4. Instala Python 3.12 o 3.13 si aún no lo tienes.

## Paso 2. Crear la configuración sin revelar la clave

1. Ejecuta **`CONFIGURAR_POSTGRESQL_WINDOWS.bat`**.
2. El asistente preguntará servidor (predeterminado `localhost`), puerto (`5432`), usuario (`postgres`), base (`salud_plc_es3`) y contraseña.
3. Si la base no existe, el asistente te ofrecerá crearla, **solo si confirmas**. Si tu usuario no tiene permiso, créala manualmente en pgAdmin: clic derecho en **Databases → Create → Database**, nombre `salud_plc_es3`.
4. Tras establecer conexión, el programa guarda la URL en `.env` y valida la creación de las **14 tablas**.

**Importante:** `.env` es privado. No lo subas al repositorio ni lo adjuntes al informe. El ZIP entregado no contiene tu contraseña.

## Paso 3. Iniciar y generar registros ficticios

1. Ejecuta **`INICIAR_WINDOWS.bat`** y espera el mensaje que confirma PostgreSQL y 14 tablas.
2. Ejecuta **`CREAR_ADMIN_WINDOWS.bat`** para crear una cuenta con una contraseña propia de 12 o más caracteres.
3. Visita <http://127.0.0.1:8000>.
4. Envía un reclamo ficticio, conserva el folio y el código privado, y consulta su estado en **Seguimiento**.
5. Inicia sesión en <http://127.0.0.1:8000/funcionarios/login> y verifica que aparece el caso en el panel.
6. Cambia la categoría, registra una observación y deriva el caso a otra unidad. Regresa al panel y comprueba su estado.
7. Crea una encuesta ficticia y abre **Reportes** como administración.
8. Cierra sesión, usa los botones **Atrás** y **Adelante** del navegador y verifica que no se recupera el panel anterior: debe mostrarse el formulario de acceso con el aviso de sesión cerrada. Inicia sesión otra vez para comprobar que el acceso vuelve a funcionar.

## Paso 4. Comprobar la base real en pgAdmin

Dentro de pgAdmin, abre `Databases → salud_plc_es3 → Schemas → public → Tables`.

Puedes ejecutar estas consultas en **Query Tool**:

```sql
-- Debe devolver 14.
SELECT COUNT(*) AS tablas_es3
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- Verifica qué tablas existen.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Lee el caso ficticio recién creado y las referencias de catálogo.
SELECT r.folio, tr.name AS tipo, c.name AS categoria,
       e.name AS estado, u.name AS unidad, r.created_at
FROM registro AS r
JOIN tipo_registro AS tr ON tr.id = r.record_type_id
LEFT JOIN categoria AS c ON c.id = r.category_id
LEFT JOIN estado_caso AS e ON e.id = r.status_id
LEFT JOIN unidad AS u ON u.id = r.unit_id
WHERE tr.name <> 'Encuesta'
ORDER BY r.created_at DESC
LIMIT 5;

-- Relaciona respuestas con las preguntas configuradas.
SELECT p.text, re.rating, r.facility
FROM respuesta_encuesta AS re
JOIN pregunta_encuesta AS p ON p.id = re.question_id
JOIN registro AS r ON r.id = re.record_id
ORDER BY re.created_at DESC
LIMIT 5;

-- Comprueba las actuaciones y auditoría real.
SELECT event_type, created_at FROM auditoria ORDER BY id DESC LIMIT 10;
```

## Paso 5. Evidencias necesarias para el profesor

Guarda capturas **de tu equipo y tu PostgreSQL real**:

| Evidencia | Qué debe verse | Rúbrica |
| --- | --- | --- |
| E-01 | Ventana que indica conexión PostgreSQL y 14 tablas | 3.1.4.7 |
| E-02 | Lista de las 14 tablas en pgAdmin | 3.1.2.3 |
| E-03 | Consulta SQL del caso ficticio y sus FK | 3.1.2.3 y 3.1.2.4 |
| E-04 | Creación web, folio y seguimiento con dato persistido | 3.1.1.1 |
| E-05 | Funcionario autorizado y acceso denegado de otra unidad | 3.1.3.5 |
| E-06 | Encuesta y respuesta vinculadas por FK | 3.1.2.3 |
| E-07 | Resultado de 50 pruebas automáticas en consola | 3.1.5 |
| E-08 | Comparación esperado/obtenido en el informe | 3.1.6 |
| E-09 | Historial real de aportes de Nicolás y Matías (commits/tareas) | 3.1.3.6 |
| E-10 | Mensaje por consentimiento no aceptado, sin salir del formulario | 3.1.1 y 3.1.5 |
| E-11 | Sesión cerrada, intento de volver con Atrás/Adelante y nuevo inicio de sesión obligatorio | 3.1.3 y 3.1.5 |

**No uses capturas de la ejecución con SQLite para afirmar que PostgreSQL funciona.** La instalación de Windows se demuestra con E-01 a E-03. Si algún paso falla, conserva la salida del error y corrige antes de entregar.

## Pruebas automáticas

Desde la terminal de VS Code, con el entorno virtual activado:

```powershell
python -m pip install pytest httpx
python -m pytest -q --junitxml=evidencias/resultado_pruebas_es3.xml
```

Las 50 pruebas automatizadas utilizan **SQLite temporal aislada**, incluida en el entorno de pruebas, para no borrar ni alterar datos del PostgreSQL académico. Además, el SQL de las 14 tablas se compila con el dialecto PostgreSQL. El conjunto incluye reportes filtrados, administración de categorías, errores amigables, protección de origen/CSRF, revocación de cookies tras salir, caducidad por inactividad y encabezados de seguridad. La experiencia con Atrás/Adelante debe capturarse visualmente en tu navegador. Esto complementa, pero no sustituye, la verificación real de E-01 a E-03.

## Si ya tienes registros de la versión anterior

El nuevo esquema no mezcla automáticamente la base SQLite previa. Si realmente necesitas conservar registros, realiza respaldo de `instance/salud_plc.sqlite3` y de `instance/session_secret.key`. Después, con PostgreSQL vacío y configurado:

```powershell
python -m app.migrar_sqlite --source instance/salud_plc.sqlite3
python -m app.migrar_sqlite --source instance/salud_plc.sqlite3 --apply
```

La primera orden solo muestra lo que importaría. La segunda exige `--apply` y **se niega a importar si ya hay cuentas, solicitudes o auditorías en PostgreSQL**, para evitar duplicar o sobrescribir información.
