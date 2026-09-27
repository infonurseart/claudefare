# NurseArt · fase 4

NurseArt es una aplicación web para el seguimiento de cuidados, gestión de medicación, comunicación asistencial y solicitudes a farmacia. Esta entrega incorpora un **expediente de verificación profesional**, una **tienda de parafarmacia con carrito** y una **PWA instalable**.

## Novedades de esta fase

| Área | Entrega |
|---|---|
| Verificación profesional | Expediente con profesión, número de colegiación, provincia/colegio, acreditación y documento identificativo. La cuenta no habilita funciones clínicas ni la vinculación de pacientes hasta que un administrador la aprueba. |
| Administración | Las cuentas aprobadas se activan mediante una Cloud Function; la función rechaza expedientes sin colegiación, identidad y estado `submitted`. |
| Farmacia | Catálogo de parafarmacia, carrito con cantidades, total estimado y envío de pedido para revisión. El flujo no realiza cobros online ni vende medicamentos sujetos a receta. |
| PWA | Manifest, iconos de 192/512 px, service worker, página offline y botón de instalación cuando el navegador admite el aviso. |
| Seguridad | Reglas de Firestore y Storage para documentos profesionales privados, profesionales aprobados y solicitudes de farmacia asociadas al código del establecimiento. |

## Requisitos

- Node.js 20 o superior.
- Una cuenta de Firebase con Authentication por email/contraseña, Firestore, Storage, Cloud Functions y Hosting activados.
- Firebase CLI autenticado con acceso al proyecto `nurseart`, o un alias de proyecto actualizado en `.firebaserc`.

## Desarrollo local

```bash
npm ci
npm run dev
```

La configuración web de Firebase se mantiene en `src/firebase.js`. Para trabajar con otro proyecto, sustituye sus valores públicos por la configuración de ese proyecto en Firebase Console.

## Pruebas y compilación

```bash
npm run build
cd functions && npm ci && npm run lint
```

## Despliegue en Firebase

El archivo `firebase.json` ya incluye Firebase Hosting para una SPA. Una vez autenticado en Firebase:

```bash
npm ci
npm run build
cd functions && npm ci && cd ..
firebase deploy --only firestore:rules,storage,functions,hosting
```

> Antes de activar cuentas reales, revisa la redacción de privacidad, retención de documentos, roles administradores y requisitos regulatorios aplicables. La aprobación de una cuenta solo se completa cuando la Cloud Function confirma un expediente enviado con los dos documentos obligatorios.

## Flujo de verificación

1. El profesional crea una cuenta y accede únicamente a **Verificación de identidad**.
2. Completa profesión, colegiación y colegio/provincia; sube acreditación e identidad.
3. Envía el expediente. El administrador revisa los archivos privados y aprueba o rechaza.
4. La función asigna el claim `profesional` y registra `verificationStatus: approved`.
5. Tras iniciar sesión de nuevo, se habilitan el panel clínico y la vinculación de pacientes.

## Flujo de tienda de farmacia

1. La farmacia registra un **código del establecimiento**.
2. El cuidador vincula la farmacia introduciendo exactamente ese código.
3. El cuidador añade productos de parafarmacia al carrito y envía una solicitud de preparación.
4. La farmacia revisa disponibilidad y precio. Cualquier cobro o dispensación ocurre fuera de la aplicación, según su proceso autorizado.

## Estructura relevante

```text
src/App.jsx                     Interfaz y lógica de cliente
src/firebase.js                 Firebase Auth, Firestore, Storage y Functions
functions/approve-professional.js  Activación segura de profesionales
firestore.rules                 Reglas de datos
storage.rules                   Reglas de archivos privados
public/manifest.webmanifest     Metadatos PWA
public/sw.js                    Caché de aplicación y modo sin conexión
```
