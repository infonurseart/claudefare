const admin = require("firebase-admin");

const uid = "9zbFOqcL2mR9jWMcRrsjz7c6VxK2";

if (!process.env.GOOGLE_APPLICATION_CREDENTIALS) {
  console.error("Falta GOOGLE_APPLICATION_CREDENTIALS con la ruta de la clave de servicio.");
  process.exit(1);
}

admin.initializeApp({
  credential: admin.credential.applicationDefault(),
  projectId: "nurseart"
});

(async () => {
  try {
    await admin.auth().setCustomUserClaims(uid, { role: "admin" });
    await admin.firestore().doc(`users/${uid}`).set({
      role: "admin",
      verificationStatus: "approved",
      updatedAt: new Date().toISOString()
    }, { merge: true });
    console.log(`Administrador configurado correctamente para ${uid}`);
    console.log("Cierra sesión y vuelve a entrar en NurseArt para renovar el token.");
  } catch (error) {
    console.error("No se pudo configurar el administrador:", error.message);
    process.exitCode = 1;
  }
})();
