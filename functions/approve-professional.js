const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

initializeApp();

function requireAdmin(request) {
  if (!request.auth || request.auth.token.role !== "admin") {
    throw new HttpsError("permission-denied", "Solo un administrador puede revisar cuentas profesionales.");
  }
}

exports.approveProfessionalAccount = onCall({ region: "europe-west1" }, async (request) => {
  requireAdmin(request);
  const { targetUid, professionalData = {} } = request.data || {};
  if (!targetUid || typeof targetUid !== "string") throw new HttpsError("invalid-argument", "Falta el identificador de la cuenta.");
const requestRef = getFirestore().doc(`professionalRequests/${targetUid}`);
const verificationRequest = await requestRef.get();
const requestData = verificationRequest.exists ? verificationRequest.data() : null;
const documents = Array.isArray(requestData?.documents) ? requestData.documents : [];
const hasRegistration = documents.some(doc => doc && doc.kind === "colegiacion" && doc.path);
const hasIdentity = documents.some(doc => doc && doc.kind === "identidad" && doc.path);
if (!requestData || requestData.status !== "submitted" || !requestData.registrationNumber || !hasRegistration || !hasIdentity) {
  throw new HttpsError("failed-precondition", "La cuenta no ha enviado el expediente profesional completo.");
}
const safeData = {
    name: String(professionalData.name || "").slice(0, 120),
    surname: String(professionalData.surname || "").slice(0, 120),
    email: String(professionalData.email || "").slice(0, 180),
    specialty: String(professionalData.specialty || "").slice(0, 120),
    role: "profesional", verificationStatus: "approved",
    approvedAt: new Date().toISOString(), approvedBy: request.auth.uid,
    updatedAt: FieldValue.serverTimestamp()
  };
  await getAuth().setCustomUserClaims(targetUid, { role: "profesional" });
  await getFirestore().doc(`users/${targetUid}`).set(safeData, { merge: true });
  await requestRef.set({ status: "approved", approvedAt: safeData.approvedAt, approvedBy: request.auth.uid }, { merge: true });
  return { approved: true, targetUid };
});

exports.rejectProfessionalAccount = onCall({ region: "europe-west1" }, async (request) => {
  requireAdmin(request);
  const { targetUid, reason = "No verificada" } = request.data || {};
  if (!targetUid || typeof targetUid !== "string") throw new HttpsError("invalid-argument", "Falta el identificador de la cuenta.");
  await getFirestore().doc(`users/${targetUid}`).set({ role: "pendiente_verificacion", verificationStatus: "rejected", rejectionReason: String(reason).slice(0, 300), rejectedAt: new Date().toISOString(), rejectedBy: request.auth.uid }, { merge: true });
  await getFirestore().doc(`professionalRequests/${targetUid}`).set({ status: "rejected", rejectionReason: String(reason).slice(0, 300), rejectedAt: new Date().toISOString(), rejectedBy: request.auth.uid }, { merge: true });
  return { rejected: true, targetUid };
});
