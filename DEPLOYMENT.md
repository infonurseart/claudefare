# Despliegue de NurseArt en Firebase

## Antes de desplegar

Confirma que el proyecto activo en `.firebaserc` es el correcto y que el usuario de Firebase CLI tiene permisos para desplegar **Hosting**, **Cloud Functions**, **Firestore Rules** y **Storage Rules**. Las reglas de esta entrega son deliberadamente restrictivas: no publiques funciones ni reglas sin probarlas primero con cuentas de cuidador, farmacia, profesional pendiente, profesional aprobado y administrador.

## Secuencia recomendada

```bash
npm ci
npm run build
cd functions && npm ci && npm run lint && cd ..
firebase deploy --only firestore:rules,storage,functions,hosting
```

Después del despliegue, inicia sesión con una cuenta de administrador y verifica que una solicitud profesional sin ambos documentos no se puede aprobar. A continuación, completa un expediente de prueba y confirma que, tras aprobarlo, la nueva sesión recibe el claim profesional y puede vincular pacientes.

## Configuración del administrador inicial

El administrador debe disponer del claim personalizado `role: admin`. El repositorio conserva `functions/assign-admin.cjs` como referencia de asignación. Ejecútalo únicamente desde un entorno con credenciales de Firebase Admin configuradas y con el UID revisado.

## PWA

La PWA usa `manifest.webmanifest` y `sw.js`. Para comprobar la instalación, usa HTTPS (Firebase Hosting lo proporciona) y abre la aplicación en Chrome para Android, Safari en iOS o Chrome de escritorio. En iOS, el usuario instala desde **Compartir → Añadir a pantalla de inicio**.
