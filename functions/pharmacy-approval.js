const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

function requireAdmin(request) {
  if (!request.auth || request.auth.token.role !== "admin") {
    throw new HttpsError("permission-denied", "Solo un administrador puede revisar farmacias.");
  }
}

function notification(message, kind, extra = {}) {
  return { id: `pharmacy-${Date.now()}`, kind, message, createdAt: new Date().toISOString(), read: false, ...extra };
}

exports.approvePharmacyRegistration = onCall({ region: "europe-west1" }, async (request) => {
  requireAdmin(request);
  const { requestId } = request.data || {};
  if (!requestId || typeof requestId !== "string") throw new HttpsError("invalid-argument", "Falta la solicitud.");
  const db = getFirestore();
  const requestRef = db.doc(`pharmacyRequests/${requestId}`);
  const snap = await requestRef.get();
  if (!snap.exists || snap.data().type !== "pharmacy_onboarding") throw new HttpsError("not-found", "Solicitud de farmacia no encontrada.");
  const data = snap.data();
  if (data.status !== "submitted") throw new HttpsError("failed-precondition", "La solicitud ya ha sido revisada.");
  const now = new Date().toISOString();
  const profile = { ...data.profile, uid: data.pharmacyUid, status: "approved", approvedAt: now };
  await db.doc(`pharmacyDirectory/${data.pharmacyUid}`).set(profile, { merge: true });
  await db.doc(`userData/${data.pharmacyUid}`).set({ pharmacyRegistration: { ...data.profile, status: "approved", approvedAt: now }, pharmacyProfile: { ...data.profile, registrationStatus: "approved" }, notifications: FieldValue.arrayUnion(notification("Tu tienda ha sido aprobada y ya puede aparecer en el directorio.", "pharmacy_approved")), updatedAt: FieldValue.serverTimestamp() }, { merge: true });
  await requestRef.set({ status: "approved", reviewedAt: now, reviewedBy: request.auth.uid }, { merge: true });
  return { success: true, requestId };
});

exports.rejectPharmacyRegistration = onCall({ region: "europe-west1" }, async (request) => {
  requireAdmin(request);
  const { requestId, reason = "La información requiere revisión" } = request.data || {};
  if (!requestId || typeof requestId !== "string") throw new HttpsError("invalid-argument", "Falta la solicitud.");
  const db = getFirestore();
  const requestRef = db.doc(`pharmacyRequests/${requestId}`);
  const snap = await requestRef.get();
  if (!snap.exists || snap.data().type !== "pharmacy_onboarding") throw new HttpsError("not-found", "Solicitud de farmacia no encontrada.");
  const data = snap.data();
  if (data.status !== "submitted") throw new HttpsError("failed-precondition", "La solicitud ya ha sido revisada.");
  const now = new Date().toISOString();
  const safeReason = String(reason).slice(0, 300);
  await db.doc(`userData/${data.pharmacyUid}`).set({ pharmacyRegistration: { ...data.profile, status: "rejected", rejectionReason: safeReason, rejectedAt: now }, notifications: FieldValue.arrayUnion(notification(`Tu solicitud de tienda ha sido rechazada: ${safeReason}`, "pharmacy_rejected", { reason: safeReason })), updatedAt: FieldValue.serverTimestamp() }, { merge: true });
  await requestRef.set({ status: "rejected", rejectionReason: safeReason, reviewedAt: now, reviewedBy: request.auth.uid }, { merge: true });
  return { success: true, requestId };
});

exports.respondPharmacyLink = onCall({ region: "europe-west1" }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Debes iniciar sesión.");
  const { requestId, decision } = request.data || {};
  if (!requestId || !["accepted", "rejected"].includes(decision)) throw new HttpsError("invalid-argument", "Decisión no válida.");
  const db = getFirestore();
  const requestRef = db.doc(`pharmacyRequests/${requestId}`);
  const snap = await requestRef.get();
  if (!snap.exists || snap.data().type !== "pharmacy_link_request") throw new HttpsError("not-found", "Solicitud de vinculación no encontrada.");
  const data = snap.data();
  const pharmacy = await db.doc(`userData/${request.auth.uid}`).get();
  const canReview = request.auth.token.role === "farmacia" || pharmacy.data()?.pharmacyProfile?.code === data.farmaciaId;
  if (!canReview) throw new HttpsError("permission-denied", "No puedes revisar esta solicitud.");
  const now = new Date().toISOString();
  const approved = decision === "accepted";
  await requestRef.set({ status: decision, reviewedAt: now, reviewedBy: request.auth.uid }, { merge: true });
  await db.doc(`userData/${data.carerUid}`).set({ farmacia: { ...data.pharmacy, estado: approved ? "vinculada" : "rechazada", reviewedAt: now }, notifications: FieldValue.arrayUnion(notification(approved ? `La farmacia ${data.pharmacy?.nombre || "seleccionada"} ha aceptado tu vinculación.` : `La farmacia ${data.pharmacy?.nombre || "seleccionada"} ha rechazado tu vinculación.`, approved ? "pharmacy_link_accepted" : "pharmacy_link_rejected") ), updatedAt: FieldValue.serverTimestamp() }, { merge: true });
  return { success: true, requestId, decision };
});
