# Demostración técnica ES3 en 10 minutos

Las orientaciones del profesor indican que **no se requiere PowerPoint**. La exposición debe mostrar la aplicación, el código, la base de datos y las pruebas, con dos minutos adicionales para preguntas.

## Antes de exponer

1. Configurar PostgreSQL y ejecutar `python -m app.verificar_postgres` hasta obtener confirmación de las 14 tablas.
2. Crear una cuenta de administrador desde consola (`python -m app.crear_admin`) sin dejar la contraseña escrita en las evidencias.
3. Preparar dos navegadores: uno para ciudadano y otro para funcionario.
4. Usar nombres, reclamos y respuestas ficticios. Guardar el folio/código generado para consultarlo durante la demostración.
5. Tener pgAdmin abierto en `salud_plc_es3`; dejar listo `evidencias/resultado_pruebas_es3.xml` y este guion.
6. Probar antes de exponer: cerrar sesión del panel, pulsar Atrás/Adelante en Chrome o Edge y confirmar que aparece el aviso de acceso denegado con invitación a iniciar sesión. Borrar la caché de desarrollo si había una versión antigua del código.

## Secuencia propuesta

| Minuto | Criterio | Acción visible |
| --- | --- | --- |
| 0:00–1:15 | 3.1.1 | Registrar reclamo ficticio con contacto consentido o adjunto de prueba. |
| 1:15–2:15 | 3.1.1 | Mostrar folio y código privado; consultar seguimiento desde portal público. |
| 2:15–3:30 | 3.1.2 | Abrir pgAdmin, mostrar las 14 tablas y consultar `registro` unido a `tipo_registro`, `categoria` y `estado_caso`. |
| 3:30–4:45 | 3.1.3 | Abrir panel, cambiar estado y registrar seguimiento; demostrar que otra unidad no puede consultar o descargar adjuntos. |
| 4:45–5:45 | 3.1.1 | Filtrar reportes por fecha inicial, final y categoría; mostrar el conteo, la gestión de categorías y un error de consentimiento en el formulario. |
| 5:45–6:45 | 3.1.2 | Consultar `respuesta_encuesta` y `pregunta_encuesta` en pgAdmin; explicar normalización e índices. |
| 6:45–7:45 | 3.1.4 | Mostrar verificación PostgreSQL, `.env.example` sin contraseñas y pasos reproducibles. |
| 7:45–9:00 | 3.1.5 | Ejecutar `python -m pytest -q`, explicar dos pruebas positivas y una negativa; cerrar sesión y comprobar el botón Atrás. |
| 9:00–10:00 | 3.1.6 | Comparar esperado/obtenido, revisar recomendaciones y ubicar evidencia de colaboración. |

## Preguntas que conviene preparar

- **¿Dónde se guardan los datos?** En la base PostgreSQL indicada en el `.env` local, a través de SQLAlchemy/Psycopg 3. Las pruebas automáticas usan otra SQLite temporal para proteger la base académica.
- **¿Cómo protegen solicitudes?** Contraseñas Argon2, token CSRF y origen válido, sesión firmada con revocación de cookies al salir, 30 minutos de inactividad, cabeceras CSP/anti-iframe y autorización por rol/unidad. El seguimiento ciudadano usa folio y código privado HMAC. Mostrar CP-33 a CP-36.
- **¿Por qué no se puede regresar al panel tras cerrar sesión?** El servidor comprueba la sesión y el registro de revocación en cada ruta; las respuestas privadas llevan `Cache-Control: no-store` y la página verifica el estado al volver desde el historial. Una copia antigua de la cookie tampoco permite ingresar otra vez.
- **¿Qué evidencia hay de integridad?** 14 tablas con FK, catálogos normalizados, UNIQUE en folio y respuesta/encuesta, CHECK de nota 1–5 y pruebas de rechazo por FK. Mostrar la consulta real en pgAdmin.
- **¿Cómo cumplen HU-07/RF07 del informe 1?** Los reportes ahora permiten filtrar por fechas inclusivas y categoría, opcionalmente por tipo; el backend aplica primero los permisos por unidad y luego calcula los indicadores. Mostrar el caso de prueba CP-24.
- **¿Puedo cambiar los motivos sin modificar código?** Administración puede crear/desactivar categorías; se registran en auditoría, «Otro» permanece disponible y los casos antiguos nunca se borran. Mostrar CP-27 y CP-28.
- **¿Se implementaron las 14 tablas de la ES2?** Sí, las 14 entidades existen en los modelos, el DDL y la creación de PostgreSQL. El framework web sigue siendo FastAPI; PostgreSQL reemplaza la persistencia SQLite del piloto anterior.
- **¿Qué falta para una entrega municipal real?** Validación con usuarios y contraparte, integración WordPress, revisión profesional de seguridad, respaldos, políticas de retención y pruebas de rendimiento.
