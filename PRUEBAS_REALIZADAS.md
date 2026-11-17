# Evidencias de pruebas locales — Evaluación Sumativa 3

Entorno: pruebas automatizadas FastAPI/TestClient + SQLite temporal separada. Todas las identidades y solicitudes son **ficticias**.

| ID | Verificación | Resultado |
|---|---|---|
| P-01 | Inicio y logo accesibles | Aprobado |
| P-02 | Registro persistente, folio privado y consulta | Aprobado |
| P-03 | Solicitud sin token CSRF | Rechazada correctamente |
| P-04 | Encuesta guardada | Aprobado |
| P-05 | Derivación Recepción → Farmacia con cambio de visibilidad | Aprobado |
| P-06 | Acceso a caso ajeno mediante petición POST | Rechazado correctamente |
| P-07 | Jefatura ve casos sin poder modificarlos | Aprobado |
| P-08 | Alta de unidad y funcionario desde administración | Aprobado |
| P-09 | Publicación de aviso informativo | Aprobado |
| P-10 | Contraseña ficticia del antiguo prototipo sin autorización | Rechazada correctamente |

No equivale a una auditoría de seguridad ni a pruebas de rendimiento de un sistema desplegado en producción.

## Ampliación ES3 del 17 de noviembre de 2026

Se ejecutaron **50 pruebas automáticas, con 50 aprobadas y 0 fallidas**, usando una SQLite temporal separada del PostgreSQL del equipo. El resultado reproducible está en `evidencias/resultado_pruebas_es3.xml`; la matriz detallada se encuentra en `ES3_IMPLEMENTACION.md`. Se agregaron siete tests de regresión ES1/ES2 y seis tests de seguridad (textos de interfaz, cabeceras de protección, origen de solicitudes, reutilización de una cookie revocada, inactividad y auditoría de acceso fallido). Las consultas repetidas no sustituyen pruebas de carga concurrente.

| ID | Nueva comprobación | Resultado automático |
| --- | --- | --- |
| P-11 | Contacto voluntario sin marcar consentimiento | HTTP 400 con error visible dentro del formulario, sin guardar caso |
| P-12 | Encuesta y adjuntos inválidos | Rechazo sin pantalla JSON crudo; mensajes HTML |
| P-13 | Cierre de sesión y acceso de nuevo al panel sin autenticación | Redirección HTTP 303 al formulario con aviso de sesión cerrada |
| P-14 | Endpoint de sesión tras salir | HTTP 401 sin información personal |
| P-15 | Pantallas privadas sin almacenamiento en caché | Cabeceras `private`, `no-store` y validación de código `pageshow`/`pagehide` |
| P-16 | Nuevo inicio de sesión después de salir | Acceso recuperado tras autenticación válida |

**Comprobación manual pendiente:** probar el botón Atrás/Adelante de Chrome o Edge en Windows después del cierre de sesión, guardar la captura del aviso y repetir la prueba sobre PostgreSQL real. Estas pruebas automatizadas verifican el control del servidor, pero no sustituyen una revisión visual del historial del navegador.
