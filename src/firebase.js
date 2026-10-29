import { initializeApp } from "firebase/app";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, onAuthStateChanged } from "firebase/auth";
import { getFirestore, doc, setDoc, getDoc, updateDoc, collection, addDoc, query, where, getDocs, orderBy, onSnapshot } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyALoBTuVGRozmrtiWMX9h89TCb30yDmDGg",
  authDomain: "nurseart.firebaseapp.com",
  projectId: "nurseart",
  storageBucket: "nurseart.firebasestorage.app",
  messagingSenderId: "142330942759",
  appId: "1:142330942759:web:5b2e294c4a8bae74014502"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

export const registerUser = async (email, password, role, name, apellido) => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    const finalRole = role === "pro" ? "pendiente_verificacion" : role;
    await setDoc(doc(db, "users", cred.user.uid), { email, role: finalRole, name: `${name} ${apellido}`.trim(), createdAt: new Date().toISOString() });
    await setDoc(doc(db, "userData", cred.user.uid), { email, role: finalRole, name: `${name} ${apellido}`.trim() });
    if (role === "pro") {
      await setDoc(doc(db, "professionalRequests", cred.user.uid), { email, name: `${name} ${apellido}`.trim(), requestedAt: new Date().toISOString(), status: "pending" });
    }
    return { success: true, uid: cred.user.uid, role: finalRole, name: `${name} ${apellido}`.trim(), email };
  } catch(e) { return { success: false, error: e.message }; }
};

export const loginUser = async (email, password) => {
  try {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    const snap = await getDoc(doc(db, "users", cred.user.uid));
    if (!snap.exists()) return { success: false, error: "Usuario no encontrado" };
    const data = snap.data();
    return { success: true, uid: cred.user.uid, role: data.role, name: data.name, email: data.email };
  } catch(e) { return { success: false, error: "Email o contraseña incorrectos" }; }
};

export const logoutUser = async () => { try { await signOut(auth); } catch(e) {} };

export const saveUserData = async (uid, data) => {
  try { await setDoc(doc(db, "userData", uid), data, { merge: true }); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const getUserData = async (uid) => {
  try { const snap = await getDoc(doc(db, "userData", uid)); return snap.exists() ? snap.data() : null; }
  catch(e) { return null; }
};

export const createInviteCode = async (proUid, code) => {
  try { await setDoc(doc(db, "inviteCodes", code), { proUid, createdAt: new Date().toISOString(), used: false }); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const createPharmacyRequest = async (carerUid, pharmacyId, reqData) => {
  try {
    const ref = await addDoc(collection(db, "pharmacyRequests"), {
      carerUid, pharmacyId, ...reqData,
      estado: "Pendiente de revisión",
      createdAt: new Date().toISOString(),
      historial: [{ fecha: new Date().toLocaleString("es-ES"), accion: "Solicitud creada", usuario: "Cuidador" }]
    });
    return { success: true, id: ref.id };
  } catch(e) { return { success: false, error: e.message }; }
};

export const getPharmacyRequests = async (pharmacyId) => {
  try {
    const snap = await getDocs(query(collection(db, "pharmacyRequests"), where("pharmacyId", "==", pharmacyId)));
    return snap.docs.map(d => ({ id: d.id, ...d.data() }));
  } catch(e) { return []; }
};

export const updateRequestStatus = async (reqId, estado, usuario) => {
  try {
    const ref = doc(db, "pharmacyRequests", reqId);
    const snap = await getDoc(ref);
    const data = snap.data();
    await updateDoc(ref, {
      estado,
      historial: [...(data.historial || []), { fecha: new Date().toLocaleString("es-ES"), accion: `Estado: ${estado}`, usuario }]
    });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const onAuthChange = (callback) => onAuthStateChanged(auth, callback);

export const resetPassword = async (email) => {
  const { sendPasswordResetEmail } = await import("firebase/auth");
  try { await sendPasswordResetEmail(auth, email); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const loadUserData = async (uid) => {
  try { const snap = await getDoc(doc(db, "userData", uid)); return snap.exists() ? snap.data() : null; }
  catch(e) { return null; }
};

export const subscribeUserData = (uid, callback) => {
  return onSnapshot(doc(db, "userData", uid), snap => callback(snap.exists() ? snap.data() : null));
};

export const registerInviteCode = async (code, carerUid) => {
  try {
    const snap = await getDoc(doc(db, "inviteCodes", code));
    if (!snap.exists()) return { success: false, error: "Código no válido" };
    const data = snap.data();
    if (data.used) return { success: false, error: "Código ya usado" };
    await updateDoc(doc(db, "inviteCodes", code), { used: true, usedBy: carerUid, usedAt: new Date().toISOString() });
    return { success: true, proUid: data.proUid };
  } catch(e) { return { success: false, error: e.message }; }
};

export const linkProCarer = async (proUid, carerUid) => {
  try {
    await setDoc(doc(db, "careTeam", `${proUid}_${carerUid}`), { proUid, carerUid, linkedAt: new Date().toISOString(), status: "active" });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const saveClinicalData = async (uid, section, data) => {
  try { await setDoc(doc(db, "clinicalData", uid), { [section]: data }, { merge: true }); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const loadClinicalData = async (uid) => {
  try { const snap = await getDoc(doc(db, "clinicalData", uid)); return snap.exists() ? snap.data() : {}; }
  catch(e) { return {}; }
};

export const subscribeClinicalData = (uid, callback) => {
  return onSnapshot(doc(db, "clinicalData", uid), snap => callback(snap.exists() ? snap.data() : {}));
};

export const uploadWoundPhoto = async (uid, file) => {
  try {
    const { getStorage, ref, uploadBytes, getDownloadURL } = await import("firebase/storage");
    const storage = getStorage();
    const storageRef = ref(storage, `wounds/${uid}/${Date.now()}_${file.name}`);
    const snapshot = await uploadBytes(storageRef, file);
    const url = await getDownloadURL(snapshot.ref);
    return { success: true, url };
  } catch(e) { return { success: false, error: e.message }; }
};

export const getCareTeam = async (uid, role) => {
  try {
    const field = role === "pro" ? "proUid" : "carerUid";
    const snap = await getDocs(query(collection(db, "careTeam"), where(field, "==", uid), where("status", "==", "active")));
    return snap.docs.map(d => ({ id: d.id, ...d.data() }));
  } catch(e) { return []; }
};

export const getCareTeamMember = async (uid) => {
  try { const snap = await getDoc(doc(db, "users", uid)); return snap.exists() ? { uid, ...snap.data() } : null; }
  catch(e) { return null; }
};

export const subscribeCareTeam = (uid, role, callback) => {
  const field = role === "pro" ? "proUid" : "carerUid";
  return onSnapshot(query(collection(db, "careTeam"), where(field, "==", uid), where("status", "==", "active")), snap => {
    callback(snap.docs.map(d => ({ id: d.id, ...d.data() })));
  });
};

export const saveCareTeamMember = async (proUid, carerUid, data) => {
  try {
    await setDoc(doc(db, "careTeam", `${proUid}_${carerUid}`), { proUid, carerUid, ...data, updatedAt: new Date().toISOString() }, { merge: true });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const revokeCareTeamMember = async (proUid, carerUid) => {
  try { await updateDoc(doc(db, "careTeam", `${proUid}_${carerUid}`), { status: "revoked", revokedAt: new Date().toISOString() }); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const createProfessionalRequest = async (uid, data) => {
  try { await setDoc(doc(db, "professionalRequests", uid), { ...data, status: "pending", createdAt: new Date().toISOString() }, { merge: true }); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};

export const getProfessionalRequests = async () => {
  try {
    const snap = await getDocs(query(collection(db, "professionalRequests"), where("status", "==", "pending")));
    return snap.docs.map(d => ({ id: d.id, ...d.data() }));
  } catch(e) { return []; }
};

export const approveProfessionalAccount = async (uid) => {
  try {
    await updateDoc(doc(db, "professionalRequests", uid), { status: "approved", approvedAt: new Date().toISOString() });
    await updateDoc(doc(db, "users", uid), { role: "pro" });
    await updateDoc(doc(db, "userData", uid), { role: "pro" });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const rejectProfessionalAccount = async (uid, reason) => {
  try {
    await updateDoc(doc(db, "professionalRequests", uid), { status: "rejected", rejectedAt: new Date().toISOString(), reason });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const uploadProfessionalDocument = async (uid, file) => {
  try {
    const { getStorage, ref, uploadBytes, getDownloadURL } = await import("firebase/storage");
    const storage = getStorage();
    const storageRef = ref(storage, `professional_docs/${uid}/${Date.now()}_${file.name}`);
    const snapshot = await uploadBytes(storageRef, file);
    const url = await getDownloadURL(snapshot.ref);
    await setDoc(doc(db, "professionalRequests", uid), { documentUrl: url, documentUploadedAt: new Date().toISOString() }, { merge: true });
    return { success: true, url };
  } catch(e) { return { success: false, error: e.message }; }
};

export const updatePharmacyRequest = async (reqId, data) => {
  try {
    const ref = doc(db, "pharmacyRequests", reqId);
    const snap = await getDoc(ref);
    const existing = snap.data() || {};
    await updateDoc(ref, {
      ...data,
      historial: [...(existing.historial || []), { fecha: new Date().toLocaleString("es-ES"), accion: data.estado || "Actualizado", usuario: data.usuario || "Sistema" }]
    });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};
