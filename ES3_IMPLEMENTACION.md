# Implementación y evidencias de la Evaluación Sumativa 3

**Proyecto:** Sistema de Gestión de Satisfacción Usuaria, Reclamos, Sugerencias y Agradecimientos para Salud Municipal Padre Las Casas. **Integrantes declarados en el informe anterior:** Nicolás Calbullanca y Matías Soto. **Asignatura:** Proyecto Integrado. **Profesor:** Manuel Alfredo Sánchez Cárcamo. **Fecha de verificación:** 17/11/2026.

## 1. Alcance implementado

Existe un portal público para ingresar reclamos, sugerencias y agradecimientos, consultar el estado mediante folio y código privado y responder encuestas anónimas. Permite adjuntar un PDF/JPG/PNG de prueba (máximo 2 MB, almacenamiento privado) y guardar un contacto voluntario solo con consentimiento. El portal interno permite iniciar sesión, revisar casos según unidad y rol, modificar estado y clasificación, registrar seguimiento, derivar casos, buscar con filtros, descargar los adjuntos autorizados y ver estadísticas **filtradas por fechas, categoría y tipo**. Administración crea unidades, cuentas y **categorías activables/desactivables**; el rol de contenidos publica avisos. El historial conserva los casos asociados a categorías desactivadas.

Es un piloto académico local con datos ficticios. **Se implementó el modelo de 14 tablas de la ES2, compatible con PostgreSQL mediante SQLAlchemy y el controlador Psycopg 3.** La conexión a un servidor PostgreSQL real deberá verificarse con el procedimiento de la sección 5 en la instalación Windows del equipo; las pruebas automáticas locales usan SQLite temporal y la compilación del DDL PostgreSQL. Se mantiene FastAPI para no reemplazar la interfaz y los flujos ya operativos; este es un cambio justificado respecto de Django REST Framework, que era la propuesta inicial, no una obligación específica de la rúbrica. WordPress, Rayen y el despliegue municipal permanecen fuera del piloto.

## 2. Matriz de trazabilidad funcional

| CU / necesidad | Ruta e implementación | Comprobación automática |
| --- | --- | --- |
| CU-01 Registrar reclamo/sugerencia/agradecimiento | `/solicitud`, `create_case`; catálogos normalizados y `registro` | `test_public_registration_persists_and_private_tracking`, `test_registro_usa_claves_foraneas_y_auditoria` |
| CU-02 Seguimiento privado | `/seguimiento`, `lookup` | `test_public_registration_persists_and_private_tracking` |
| CU-03 Encuestas anónimas | `/encuesta`; `registro` + `pregunta_encuesta` + `respuesta_encuesta` | `test_survey_persisted`, `test_respuesta_encuesta_depende_de_registro_y_pregunta` |
| CU-04 Autenticación y permisos | `/funcionarios/login`, `app/security.py`, `logout`, `/funcionarios/sesion-actual` | `test_employee_login_and_case_scope`, `test_official_scope_enforced_in_post`, `test_logout_blocks_old_panel_and_forces_login`, `test_session_notice_and_relogin_restore_access` |
| CU-05 Actualizar estado e historial | `/funcionarios/casos/{id}`, `update_case` | `test_employee_login_and_case_scope` |
| CU-06 Derivar y reclasificar | `update_case`, `CaseEvent` | `test_reclassification_persists_and_is_audited`, `test_reclassification_rejects_unlisted_category` |
| CU-07 Reportes y satisfacción | `/funcionarios/reportes`, `reports`; filtros inclusivos por período, motivo y tipo | `test_survey_statistics_are_restricted_by_role`, `test_report_filters_by_inclusive_period_category_and_type`, `test_report_respects_unit_scope_before_filtering` |
| CU-08 Administración y contenidos | `/funcionarios/unidades`, `/categorias`, `/equipo`, `/avisos` | `test_admin_adds_unit_and_staff`, `test_admin_creates_category_used_by_public_forms_and_reports`, `test_admin_notice_published_publicly` |
| CU-09 Buscar, filtrar y paginar casos | `/funcionarios/panel`, `dashboard` | `test_filters_do_not_reveal_cases_from_other_units`, `test_pagination_caps_list_and_preserves_search` |
| CU-10 Contacto consentido y adjuntos privados | `/solicitud`, `/funcionarios/adjuntos/{id}` | `test_contacto_voluntario_y_adjunto_con_descarga_por_rol`, `test_contacto_sin_permiso_y_adjunto_invalido_rechazados` |

Cobertura declarada: **10 de 10 procesos operativos** de esta versión ES3 disponen de pruebas asociadas. No equivale a 100 % de toda la propuesta institucional y no incluye pruebas de carga ni de usuarios finales.

### Relación explícita con lo comprometido en ES1 y ES2

| Requisito de los informes anteriores | Evidencia en ES3 | Estado |
| --- | --- | --- |
| HU-01 / RF01: encuesta ciudadana anónima | `/encuesta`, `respuesta_encuesta` y estadísticas por rol | Implementado y probado |
| HU-02, HU-03 / RF02: reclamos, sugerencias y agradecimientos | `/solicitud`, `tipo_registro`, folio único y categorías | Implementado y probado |
| HU-04 / RF06: seguimiento de reclamos | `/seguimiento`, folio más código privado HMAC | Implementado y probado |
| HU-05 / RF03: clasificar, incluida «Otro» | Edición de caso y catálogo administrable con «Otro» obligatorio | Implementado y probado |
| HU-06 / RF04–RF05: derivación, responsable, estados e historial | `/funcionarios/casos/{id}`, unidad, estado y seguimiento | Implementado y probado |
| HU-07 / RF07: reportes filtrables por período y categoría | `/funcionarios/reportes?desde=...&hasta=...&category=...`; filtros incluyentes y ámbito de rol | Implementado y probado |
| HU-08 / RF08: avisos públicos sin apoyo técnico | `/funcionarios/avisos` para contenido/admin | Implementado y probado |
| RF09 / RNF02: perfiles diferenciados | `app/security.py` y permisos en servidor | Implementado y probado |
| RF10 / RNF03: anonimato y contacto opcional | Ciudadano nullable, consentimiento explícito y adjuntos privados | Implementado y probado |
| RF12 / RNF06: fecha, canal y auditoría | `created_at`, `canal`, `seguimiento` y `auditoria` | Implementado y probado |
| RNF05: accesibilidad | Etiquetas, mensajes visibles y diseño adaptable; falta auditoría WCAG con usuarios reales | Parcial; requiere evaluación humana |
| RNF04: disponibilidad | Ejecución local y controles de sesión; faltan monitoreo, respaldo y alta disponibilidad | Parcial; ambiente de producción pendiente |
| RF11 / RNF07: tótems y nuevos canales | El diseño reserva `canal` para extensibilidad; no existen tótems físicos | Etapa futura declarada en ES1/ES2 |
| Propuesta WordPress y conexión municipal | Portal independiente FastAPI; sin credenciales ni autorización institucional | Integración externa pendiente |

Los requisitos de futuro (tótems, Rayen, WordPress institucional), la colaboración individual y la validación municipal **no** se presentan como completos. Se necesita autorización y evidencia real para ellos.

## 3. Modelo de datos e integridad

| Tabla | Función | Restricciones, índices y relaciones |
| --- | --- | --- |
| `rol` | Perfiles de permisos | Código único y relación 1:N con funcionarios |
| `unidad` | Unidades responsables | Nombre único; FK desde funcionarios, casos y seguimientos |
| `usuario_admin` | Funcionarios y credenciales | FK obligatorias a rol y unidad; correo único; contraseña Argon2 |
| `tipo_registro` | Reclamo, sugerencia, agradecimiento y encuesta | Nombre único; FK obligatoria en registro |
| `canal` | Origen de ingreso | Catálogo Portal web; FK obligatoria en registro |
| `categoria` | Motivo o aspecto de atención | Nombre único; FK en registro |
| `estado_caso` | Estado administrativo | Catálogo normalizado; FK en registro y seguimiento |
| `ciudadano` | Contacto voluntario | Consentimiento y datos opcionales; FK nullable en registro |
| `registro` | Solicitudes y encuestas | Folio único, HMAC, FK a catálogos, ciudadano y unidad; índices por estado/fecha |
| `seguimiento` | Historial de cambios | FK a registro, actor, estado y unidad destino |
| `pregunta_encuesta` | Preguntas habilitadas | Código único; pregunta general inicial |
| `respuesta_encuesta` | Calificación anónima | FK a registro y pregunta, UNIQUE del par, CHECK 1–5 |
| `adjunto` | Archivo asociado a solicitud | FK a registro, clave privada única y tamaño no negativo |
| `auditoria` | Eventos de cambios, ingresos y avisos | FK opcionales; detalles JSONB en PostgreSQL |

Se aplica integridad referencial real en PostgreSQL y en SQLite temporal de pruebas (`PRAGMA foreign_keys=ON`). Las restricciones `CHECK` de calificaciones, longitud HMAC y tamaño de adjuntos se aplican en el esquema nuevo. Los catálogos evitan repetir textos libres de estado, rol, tipo o motivo en cada registro. Las preguntas permiten ampliar encuestas sin crear columnas nuevas. El DDL PostgreSQL se genera automáticamente desde el mismo ORM, por lo que el SQL y los modelos comparten definición.

El [diagrama real de 14 entidades](evidencias/modelo_14_entidades_es3.png) y [script PostgreSQL](evidencias/esquema_postgresql_es3.sql) corresponden a `app/models.py`, no solo a una propuesta conceptual. La fuente editable es `evidencias/modelo_14_entidades_es3.dot`. Las vistas `evidencias/vista_inicio_final.png`, `evidencias/vista_formulario_final.png`, `evidencias/vista_detalle_final.png` y `evidencias/vista_reportes_filtros.png` son representaciones impresas del HTML producido por TestClient con datos ficticios. No son capturas de la BD Windows ni reemplazan la demostración en Chrome/Edge.

El [documento de comprobación para Windows](ES3_POSTGRESQL.md) detalla consultas en pgAdmin y evidencias que debe capturar el equipo para demostrar que las 14 tablas están creadas en su PostgreSQL real.

## 4. Seguridad y programación

- Contraseñas protegidas con Argon2; la primera cuenta se crea con `python -m app.crear_admin` sin clave predefinida. Una política de complejidad, comprobada en el servidor tanto al crear funcionarios como al crear la primera cuenta administradora, exige entre 12 y 200 caracteres, mayúscula, minúscula, número y símbolo. El formulario de funcionarios muestra el requisito y bloquea el envío inválido con un mensaje accesible. No se cambia la verificación de inicio de sesión de cuentas anteriores.
- Cookies de sesión firmadas, `HttpOnly`, `SameSite=Lax` y expiración de dos horas. La opción `COOKIE_SECURE=1` exige HTTPS.
- Token CSRF verificado en todos los formularios POST. En la ejecución local (`127.0.0.1`/`localhost`), la validez del token evita bloqueos falsos por encabezados Origin alterados por el navegador o un proxy; en conexiones no locales, se comprueban además Origin y Fetch Metadata para rechazar solicitudes ajenas.
- Revocación de la sesión en servidor mediante eventos inmutables `inicio_sesion` y `cierre_sesion` de auditoría. Una cookie firmada que se copió antes de cerrar sesión queda invalidada; el código también caduca a los 30 minutos sin actividad. No se modifica la estructura de las 14 tablas.
- Registro de intentos fallidos de inicio de sesión en auditoría, sin almacenar contraseñas ni tokens privados. El límite de intentos por IP sigue siendo apropiado únicamente para un piloto local.
- Cabeceras `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` y `Permissions-Policy`. Se eliminó JavaScript embebido en atributos HTML para respetar la política de scripts del propio origen. `Strict-Transport-Security` solo se agrega cuando se utiliza HTTPS y `COOKIE_SECURE=1`.
- Autorización en servidor: un funcionario de unidad ve solo los casos de su unidad, jefatura consulta sin editar, administración tiene alcance general y contenidos solo gestiona avisos.
- El seguimiento público verifica folio y código mediante HMAC y nunca devuelve notas internas ni descripción del caso.
- Validaciones en servidor de longitudes, campos obligatorios, estados, categorías, establecimientos y rangos de encuesta; límite de solicitudes por IP adecuado únicamente para pruebas locales.
- Adjuntos de 2 MB como máximo, detección de firma PDF/PNG/JPG, nombres de almacenamiento aleatorios fuera de `static` y descarga solo por funcionarios con acceso al caso. No equivale a antivirus ni a un sistema institucional de gestión documental.
- Contacto opcional solo con consentimiento explícito. Para evaluación no introducir datos personales reales.
- Validación visible previa al envío: datos de contacto sin consentimiento, correo incorrecto, campos obligatorios y archivos inválidos muestran un aviso en el formulario sin redirigir a una respuesta JSON. El backend repite las comprobaciones y devuelve HTML con el error.
- Al cerrar sesión, el servidor elimina el contenido de la cookie de sesión y conduce al inicio de sesión. Acceder a rutas protegidas sin sesión retorna una redirección al login con el mensaje de bloqueo; todas las respuestas `/funcionarios` tienen `Cache-Control` restrictivo, `Pragma: no-cache` y `Expires: 0`.
- La interfaz usa eventos `pagehide` y `pageshow` para ocultar el panel almacenado por Atrás/Adelante y verificar por servidor `/funcionarios/sesion-actual` antes de volver a mostrarlo. Esto complementa las restricciones obligatorias del backend y evita depender solo del JavaScript.
- Las pantallas ya no muestran frases técnicas o de evaluación («entorno académico», «base local de pruebas»). Se mantuvieron indicaciones de consentimiento y privacidad apropiadas para el ciudadano; los límites del piloto permanecen declarados en la documentación, no en la interfaz.

## 5. Instalación reproducible

**Entorno de comprobación automática:** Linux, Python 3.12, FastAPI, SQLAlchemy 2 y SQLite temporal; compilación de DDL PostgreSQL. **Entorno objetivo del alumno:** Windows, PostgreSQL 14+, Psycopg 3 y Python 3.12/3.13. La conexión del equipo debe probarse; no afirmar que se ha verificado sin el resultado del configurador.

1. Instalar PostgreSQL 14+ y Python 3.12/3.13 en Windows; comprobar servicio en ejecución.
2. Ejecutar `CONFIGURAR_POSTGRESQL_WINDOWS.bat` y elegir una base de datos nueva, normalmente `salud_plc_es3`. El asistente valida credenciales y guarda la URL local sin imprimirla.
3. Ejecutar `INICIAR_WINDOWS.bat`; se comprueban la conexión y las 14 tablas y se crean catálogos.
4. Crear cuenta con `CREAR_ADMIN_WINDOWS.bat`; elegir clave personal de 12 o más caracteres.
5. Visitar `http://127.0.0.1:8000` y `/funcionarios/login`.
6. Ingresar una solicitud ficticia con adjunto, seguir folio, iniciar sesión, cambiar estado y comprobar persistencia en pgAdmin.
7. Ejecutar `python -m pip install pytest httpx` y `python -m pytest -q`; obtener XML para evidencia.

`.env` configura el PostgreSQL real y está excluido de Git. Una SQLite local solo es alternativa técnica de desarrollo si `DATABASE_URL` no existe; el lanzador Windows ES3 exige configurar PostgreSQL. Hay importación opcional no destructiva desde SQLite antigua mediante `app.migrar_sqlite`.

## 6. Protocolo y resultados de pruebas

El protocolo usa `pytest` y `TestClient`, una base SQLite temporal distinta de la real, cuentas ficticias de prueba y reinicialización antes de cada caso. Cada prueba ejecuta un proceso HTTP, verifica respuesta y, cuando corresponde, consulta el registro persistido o el control de permisos.

**Resultado local actualizado el 18/11/2026:** 59 pruebas aprobadas, 0 fallidas. Una advertencia de deprecación `httpx`/`starlette.testclient` no alteró los resultados. El archivo `evidencias/resultado_pruebas_es3.xml` conserva el registro JUnit generado por `pytest`. Estos resultados no equivalen a una ejecución contra la instalación PostgreSQL del estudiante ni reemplazan una prueba manual del historial del navegador.

| ID | Datos / escenario | Resultado esperado | Resultado observado |
| --- | --- | --- | --- |
| CP-01 | Reclamo válido con descripción de 15+ caracteres | Guardar folio, HMAC e historial | Guardados; aprobado |
| CP-02 | Descripción corta o categoría inexistente | Rechazar sin persistir | HTTP 400, sin registro; aprobado |
| CP-03 | Solicitud sin CSRF válido | Rechazar | HTTP 403; aprobado |
| CP-04 | Consulta con código correcto / incorrecto | Mostrar estado solo con ambos datos correctos | Consulta correcta y rechazo comprobados; aprobado |
| CP-05 | Encuesta nota 5 / nota 6 | Guardar 5 y rechazar 6 | Validado; aprobado |
| CP-06 | Funcionario Farmacia consulta caso de Recepción | Ocultar y bloquear actualización | Sin fila y POST 403; aprobado |
| CP-07 | Recepción deriva caso a Farmacia | Registrar cambio de unidad e historial | Nueva unidad ve caso, anterior deja de verlo; aprobado |
| CP-08 | Jefatura intenta editar | Permitir lectura, negar edición | HTTP 200 y 403; aprobado |
| CP-09 | Reclasificar de Trato a Farmacia | Persistencia y auditoría del cambio | Categoría e historial actualizados; aprobado |
| CP-10 | Filtros de folio/estado/categoría | Resultados correctos y autorizados | Comprobado; aprobado |
| CP-11 | 23 casos y páginas inválidas | Páginas de 20+3, errores 400/404 | Comprobado; aprobado |
| CP-12 | Encuestas 3 y 5 con distintos roles | Promedio 4,0 solo para administración/jefatura | Comprobado; aprobado |
| CP-13 | Nota 0, FK inexistente, estado inválido | Restricciones de base rechazan | `IntegrityError` tres veces; aprobado |
| CP-14 | Alta de unidad, funcionario y aviso | Persistencia y publicación | Operaciones comprobadas; aprobado |
| CP-15 | Esquema 14 tablas, PK, FK y catálogos | Definición relacional completa | Inspección de 14 tablas; aprobado |
| CP-16 | Registro con tipo/estado/categoría normalizados y bitácora | Guardar y relacionar | FK y evento `auditoria`; aprobado |
| CP-17 | Encuesta con registro y pregunta | FK y nota 1–5 | Relación comprobada; aprobado |
| CP-18 | Rol inexistente y SQL PostgreSQL compilado | Rechazo FK y SQL válido | Integridad y sintaxis ORM compilada; aprobado |
| CP-19 | Contacto consentido y PDF privado | Guardar, autorizar descarga | Acceso autorizado 200 y denegado 404; aprobado |
| CP-20 | Correo sin consentimiento y falso PDF | Rechazar ambos | HTTP 400, sin guardar; aprobado |
| CP-21 | Formulario con contacto sin aceptar autorización | Avisar dentro del formulario y conservar datos | HTTP 400 con HTML, sin guardar; aprobado |
| CP-22 | Encuesta incorrecta, archivo demasiado grande y CSRF inválido | Mostrar error amigable, nunca JSON crudo | Formularios HTML y página de error institucional; aprobado |
| CP-23 | Cerrar sesión y usar el historial Atrás/Adelante | No recuperar panel ni caso, informar que debe ingresar de nuevo | Sesión 401, rutas privadas 303 al login, cabeceras no-store; aprobado a nivel HTTP; comprobación visual en Windows pendiente |
| CP-24 | Filtrar reportes con dos fechas iguales, motivo y tipo | Incluir casos del día completo, rechazar registros de fuera del intervalo | Conteo y extremos de fecha comprobados; aprobado |
| CP-25 | Fechas imposibles, rango invertido, categoría inexistente | Rechazar con página HTML, no JSON ni resultado engañoso | HTTP 400 HTML; aprobado |
| CP-26 | Funcionario de otra unidad consulta informe filtrado | No incluir casos ajenos incluso con categoría válida | 0 resultados frente a 1 de jefatura; aprobado |
| CP-27 | Admin crea categoría y ciudadano la usa | Disponibilidad en formularios, persistencia y reporte | Formulario, caso, bitácora e indicador comprobados; aprobado |
| CP-28 | Desactivar categoría con casos históricos | Ocultar a nuevos ingresos, conservar casos y filtros históricos | Casos siguen consultables; POST nuevo rechazado; aprobado |
| CP-29 | Crear duplicada, POST sin CSRF y desactivar «Otro» | Rechazos controlados y «Otro» siempre activa | 400/403 según escenario; aprobado |
| CP-30 | Consultar 30 veces un reporte y cerrar sesión | Resultados consistentes; al salir, no acceder al informe | 30 respuestas 200, luego 303; aprobado |
| CP-31 | Interfaz ciudadana con textos definitivos | No mostrar avisos de desarrollo en Inicio, formularios ni login | Cuatro rutas verificadas; aprobado |
| CP-32 | Respuestas con cabeceras de seguridad | Bloquear iframes y scripts ajenos; no permitir MIME sniffing | CSP, X-Frame-Options, nosniff y sin handlers inline; aprobado |
| CP-33 | Origen externo con CSRF válido en entorno no local; origen distinto en equipo local | Rechazar origen ajeno remotamente; admitir envío local con token válido | HTTP 403 no local; HTTP 200 local con token válido; token incorrecto siempre 403; aprobado |
| CP-34 | Reutilizar cookie antigua tras cerrar sesión | Revocar el identificador en auditoría y negar acceso | HTTP 303/401; auditoría de cierre comprobada; aprobado |
| CP-35 | Cookie de sesión inactiva 31 minutos | Exigir nueva autenticación | Redirección al login; aprobado |
| CP-36 | Acceso con contraseña incorrecta | Rechazar sin guardar contraseña; conservar evento de auditoría | HTTP 401 y evento sin secreto; aprobado |
| CP-37 | Política de complejidad en cuentas nuevas | Rechazar contraseña solo numérica, sin mayúscula/minúscula/número/símbolo o demasiado corta; aceptar una que cumpla y mostrar error en el formulario | 9 pruebas adicionales: rechazos, aceptación y alta de usuario en servidor; aprobado |

Los 37 grupos resumen las 59 funciones de prueba en `tests/test_workflow.py`, `tests/test_es3.py`, `tests/test_es3_modelo.py`, `tests/test_form_errors.py`, `tests/test_session_history.py`, `tests/test_es1_es2_requirements.py`, `tests/test_security_hardening.py` y `tests/test_password_policy.py`. Los resultados no demuestran ejecución contra PostgreSQL Windows, pruebas institucionales de rendimiento, accesibilidad o seguridad ofensiva. La repetición CP-30 **no es** una prueba de carga concurrente. El caso CP-23 requiere además navegar realmente en un navegador del equipo expositor.

## 7. Comparación y mejoras

| Hallazgo inicial | Acción implementada | Reprueba | Estado |
| --- | --- | --- | --- |
| SQLite no obligaba a cumplir FK por defecto | Activar `PRAGMA foreign_keys=ON` | CP-13 rechaza unidad inexistente | Corregido |
| Panel sin filtros ni paginación | Añadir filtros por servidor, control de ámbito y 20 filas/página | CP-10 y CP-11 | Corregido |
| Categoría no editable internamente | Añadir reclasificación con evento auditable | CP-09 | Corregido |
| Reportes limitados a tipo y estado | Añadir motivos, establecimientos y distribución de encuestas | CP-12 | Corregido |
| ES1 exigía reportes con período y categoría, pero la pantalla mostraba solo totales | Agregar filtros inclusivos por fechas, categoría y tipo con validación y alcance por rol | CP-24 a CP-26 | Corregido |
| ES2 describía categorías configurables, pero estaban fijas en código | Alta, activación/desactivación auditada y protección de «Otro»; preservar históricos | CP-27 a CP-29 | Corregido |
| ES2 diseñó 14 tablas, backend anterior usaba 6 | Modelar 14 tablas, FK, índices y catálogos; adaptar flujos | CP-15 a CP-18 + diagrama generado | Corregido en código |
| Backend anterior solo probaba SQLite | Incorporar Psycopg, configurador Windows y verificador PostgreSQL | `python -m app.verificar_postgres` en equipo alumno | Pendiente evidencia externa |
| Adjuntos y ciudadano solo figuraban en diseño | Formulario opcional, consentimiento, archivo privado y permisos | CP-19 y CP-20 | Corregido en código |
| Errores de validación redirigían a una pantalla negra con JSON | Mensajes en el mismo formulario y página HTML temática para errores HTTP | CP-21 y CP-22 | Corregido en código |
| El historial podía mostrar una vista anterior tras cerrar sesión | Sesión comprobada en cada solicitud, no-store y revalidación al volver | CP-23 | Corregido en código; validar visualmente en Windows |
| Cookie antigua aún podría estar firmada después de cerrar sesión | Identificadores aleatorios, auditoría de revocación y caducidad por inactividad | CP-34 y CP-35 | Corregido en código |
| Formularios con token CSRF válidos enviados desde otro origen fuera de la máquina local | Comprobación del encabezado Origin y rechazo en servidor; en loopback prevalece el token CSRF | CP-33 | Corregido en código |
| Falta de cabeceras de defensa y controlador inline | CSP, anti-iframe, nosniff y eventos de JavaScript externos | CP-32 | Corregido en código |
| Mensajes de desarrollo visibles al ciudadano | Sustituir por textos de atención, privacidad y seguimiento | CP-31 | Corregido en interfaz |
| Inicio de sesión fallido sin registro | Auditar intento rechazado sin contraseña ni token | CP-36 | Corregido en código |
| Sin validación real en municipio o pruebas de carga | Proponer prueba con usuarios y rendimiento en ambiente autorizado | Protocolo futuro | Pendiente |

## 8. Límites y referencias

No se han realizado pruebas de carga concurrente, auditoría externa, integración WordPress, CRUD documentado contra el PostgreSQL Windows del alumno ni validación formal con usuarios. El equipo aportó capturas de la conexión y de 14 tablas en su PostgreSQL 18, pero faltan capturas del flujo CRUD real y del historial del navegador después de cerrar sesión. La MFA se propuso como recomendación de la ES2 y **no está implementada**. Antes de uso real se requieren procesos OIRS confirmados, HTTPS con certificado, medidas de privacidad/retención, respaldo, monitoreo, antivirus para adjuntos y controles antiabuso distribuidos. **Quitar el aviso académico de las pantallas no convierte este piloto en un sistema autorizado para procesar datos reales.**

**Documentos de referencia:** Rúbrica de Evaluación Sumativa 3, Guía de Desarrollo y Evidencias ES3, Plantilla Informe 3 y el Informe Final Salud Municipal Padre Las Casas de octubre de 2026. **Repositorio de origen:** <https://github.com/NicolasPROGRA/Proyecto_Integrado> (debe actualizarse con esta versión antes de citarla como publicada). **Anexos:** `tests/`, `evidencias/`, `ES3_DEMOSTRACION.md`.

**Trabajo colaborativo:** el documento anterior identifica a Nicolás Calbullanca y Matías Soto. La distribución precisa de aportes individuales no se puede comprobar solo por el código y debe completarse con las evidencias de commits/tareas reales; no se atribuyen contribuciones sin verificar.
