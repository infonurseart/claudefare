# NurseArt — separación de entornos

## Demo

La demo utiliza datos ficticios y se emplea para presentaciones, diseño y pruebas de navegación. No deben introducirse nombres reales, fotografías clínicas, medicación real identificable ni datos de contacto de pacientes.

## Piloto

El piloto requiere una aplicación Firebase independiente o un proyecto separado, usuarios autorizados, reglas de acceso revisadas, copias de seguridad, registro de incidencias y una versión congelada. La base de datos de demo no debe reutilizarse para el piloto.

## Producción

Producción solo debe activarse después de la aprobación institucional, clínica, ética y de protección de datos. Requiere soporte, monitorización, gestión de cambios, auditoría, procedimiento de incidentes y responsable operativo.

## Variable de entorno

El proyecto admite la variable `VITE_NURSEART_ENV` con los valores `demo`, `pilot` o `production`. La configuración de Firebase debe ser distinta para cada entorno. Nunca debe incluirse una clave privada en el frontend.

Ejemplo:

```bash
VITE_NURSEART_ENV=demo
VITE_FIREBASE_PROJECT_ID=nurseart-demo
```

La configuración actual todavía conserva valores de Firebase en `src/firebase.js`; antes de un piloto deben trasladarse a variables de entorno y asignarse proyectos separados. La configuración pública de Firebase no sustituye a las reglas de seguridad de Firestore y Storage.
