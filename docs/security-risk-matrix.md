# NurseArt — matriz inicial de riesgos

La valoración final del impacto debe ser aprobada por la organización responsable del proceso. La probabilidad no debe basarse únicamente en históricos: debe revisarse mediante escenarios plausibles y pruebas internas.

| ID | Activo/proceso | Escenario de riesgo | Impacto | Probabilidad inicial | Controles requeridos | Propietario | Estado |
|---|---|---|---|---|---|---|---|
| R01 | Datos clínicos | Un cuidador accede a datos de otro usuario | Muy alto | Media | Reglas Firestore, pruebas de autorización, revisión de logs | Responsable de seguridad | Abierto |
| R02 | Fotografías de heridas | URL o almacenamiento accesible fuera del equipo autorizado | Muy alto | Media | Reglas Storage, expiración o control de acceso, no publicar enlaces | Responsable técnico | Abierto |
| R03 | Medicación | El usuario interpreta la app como prescripción | Muy alto | Baja | Avisos clínicos, contenido aprobado, no modificar pauta desde la app | Responsable clínico | En revisión |
| R04 | Farmacia | Se interpreta una solicitud como dispensación confirmada | Alto | Media | Estados explícitos, farmacia colaboradora identificada, confirmación externa | Responsable farmacia | En revisión |
| R05 | Sincronización | Se pierde un registro clínico por conflicto local/Firebase | Alto | Media | Auditoría, reintentos, marca de última sincronización, pruebas offline | Responsable técnico | Abierto |
| R06 | Cuenta | Contraseña comprometida o sesión compartida | Alto | Media | Firebase Auth, recuperación, cierre de sesión, educación al usuario | Responsable técnico | En revisión |
| R07 | Disponibilidad | Caída del servicio durante una tarea asistencial | Alto | Media | Estado offline, canal alternativo, no depender de NurseArt para urgencias | Equipo clínico/técnico | Abierto |
| R08 | Incidencia | No existe canal operativo para reportar un problema | Alto | Media | Registro de incidencias, responsable y plazo de respuesta | Investigador principal | Abierto |
| R09 | Datos demo | Se introducen datos reales en el entorno de demostración | Muy alto | Media | Banner DEMO, base separada, usuarios ficticios, bloqueo de piloto | Responsable técnico | En implementación |
| R10 | Acceso profesional | Se mantiene acceso después de revocar vinculación | Muy alto | Baja | Revocación server-side, pruebas de permisos, revisión de careTeam | Responsable de seguridad | Abierto |

## Escenarios prioritarios de prueba

Antes del piloto deben ejecutarse pruebas de acceso cruzado, revocación de permisos, subida y lectura de fotografías, pérdida de conexión durante un registro, duplicación de solicitudes y recuperación de cuenta. Cada prueba debe conservar fecha, usuario de prueba, resultado, evidencia y responsable de cierre.

## Criterio de aceptación

No se acepta el inicio del piloto con un riesgo crítico sin control compensatorio aprobado por la organización. Los riesgos de acceso indebido, exposición de imágenes clínicas y pérdida de datos requieren resolución técnica, no solo instrucciones al usuario.
