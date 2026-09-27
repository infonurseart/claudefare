# Activación del panel administrativo de NurseArt

La interfaz ya crea solicitudes reales en `professionalRequests/{uid}`. La aprobación no se ejecuta desde el navegador: se realiza mediante `functions/approve-professional.js`, que exige un claim firmado `role: admin`, asigna `role: profesional` al usuario aprobado y actualiza la solicitud.

## Primer administrador

El primer administrador debe recibir el claim mediante un proceso seguro fuera del navegador, usando Firebase Admin SDK o Firebase CLI con credenciales de servidor. No se debe añadir una contraseña administrativa en el frontend.

Ejemplo conceptual con Firebase Admin SDK:

```js
await getAuth().setCustomUserClaims(ADMIN_UID, { role: "admin" });
```

Después, el administrador debe cerrar sesión y volver a entrar para que Firebase renueve su token.

## Despliegue

Desde la raíz del proyecto, con Firebase CLI autenticado y el proyecto `nurseart` seleccionado:

```bash
cd functions
npm install
cd ..
firebase deploy --only functions,firestore:rules,storage
```

El despliegue de Functions y reglas modifica permisos reales y debe hacerse primero en un proyecto de pruebas si hay datos clínicos existentes.

## Flujo final

1. Un profesional se registra.
2. La cuenta queda como `pendiente_verificacion`.
3. Se crea `professionalRequests/{uid}` con estado `pending`.
4. Un administrador entra en el panel.
5. El panel obtiene las solicitudes pendientes.
6. Al aprobar, la función backend valida el claim del administrador.
7. Firebase asigna el claim `role: profesional`.
8. La cuenta pasa a `verificationStatus: approved`.
9. El profesional debe volver a iniciar sesión para recibir el nuevo claim.

También existe `rejectProfessionalAccount`, que deja la solicitud en estado `rejected` y conserva el motivo y la fecha.
