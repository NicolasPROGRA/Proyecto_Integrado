# Evidencias de pruebas locales — MVP 0.1

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
