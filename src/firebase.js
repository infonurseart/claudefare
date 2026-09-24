import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc, getDoc, onSnapshot, collection, addDoc, query, where, getDocs, updateDoc, doc as firestoreDoc } from "firebase/firestore";
import { getStorage, ref, uploadBytes, getDownloadURL } from "firebase/storage";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, onAuthStateChanged, sendPasswordResetEmail } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyALoBTuVGRozmrtiWMX9h89TCb30yDmDGg",
  authDomain: "nurseart.firebaseapp.com",
  projectId: "nurseart",
  storageBucket: "nurseart.firebasestorage.app",
  messagingSenderId: "142330942759",
  appId: "1:142330942759:web:5b2e294c4a8bae74014502"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const storage = getStorage(app);
export const auth = getAuth(app);

export const registerUser = async (email, password, role, name) => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    const requestedRole = role === "pro" ? "profesional" : role === "farmacia" ? "farmacia" : "cuidador";
    const accountRole = role === "pro" ? "pendiente_verificacion" : requestedRole;
    await setDoc(doc(db, "users", cred.user.uid), { email, role: accountRole, requestedRole, verificationStatus: role === "pro" ? "pending" : "not_required", name, createdAt: new Date().toISOString() });
    return { success: true, uid: cred.user.uid };
  } catch(e) {
    const msgs = {
      "auth/email-already-in-use": "Este correo ya está registrado",
      "auth/weak-password": "La contraseña debe tener al menos 6 caracteres",
      "auth/invalid-email": "Correo electrónico no válido"
    };
    return { success: false, error: msgs[e.code] || e.message };
  }
};

export const loginUser = async (email, password) => {
  try {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    const uid = cred.user.uid;
    let name = cred.user.displayName || "";
    let role = "";
    let roleStatus = "active";
    const userSnap = await getDoc(doc(db, "users", uid));
    if(userSnap.exists()){
      const d = userSnap.data();
      name = d.name || name;
      role = d.role || "";
      roleStatus = d.verificationStatus || roleStatus;
    }
    const dataSnap = await getDoc(doc(db, "userData", uid));
    if(dataSnap.exists()){
      const d = dataSnap.data();
      if(d.proProfile?.name) name = d.proProfile.name;
      if(d.pacProfile?.name) name = d.pacProfile.name;
      if(d.role) role = d.role;
    }
    return { success: true, uid, role, roleStatus, name, email };
  } catch(e) {
    const msgs = {
      "auth/user-not-found": "No existe una cuenta con este correo",
      "auth/wrong-password": "Contraseña incorrecta",
      "auth/invalid-credential": "Correo o contraseña incorrectos",
      "auth/too-many-requests": "Demasiados intentos. Espera unos minutos"
    };
    return { success: false, error: msgs[e.code] || "Error al iniciar sesión" };
  }
};

export const logoutUser = () => signOut(auth);
export const resetPassword = async (email) => {
  try { await sendPasswordResetEmail(auth, email); return { success: true }; }
  catch(e) { return { success: false, error: "No se pudo enviar el correo" }; }
};
export const onAuthChange = (callback) => onAuthStateChanged(auth, callback);

export const saveUserData = async (uid, data) => {
  try { await setDoc(doc(db, "userData", uid), {...data, updatedAt: new Date().toISOString()}, { merge: true }); }
  catch(e) { console.log("Error guardando perfil:", e.message); }
};
export const loadUserData = async (uid) => {
  try { const snap = await getDoc(doc(db, "userData", uid)); return snap.exists() ? snap.data() : null; }
  catch(e) { return null; }
};
export const subscribeUserData = (uid, callback) => onSnapshot(doc(db, "userData", uid), snap => { if(snap.exists()) callback(snap.data()); });

// Datos clínicos separados del perfil: una ficha por paciente/cuidador.
export const saveClinicalData = async (patientUid, data) => {
  try {
    await setDoc(doc(db, "patientClinical", patientUid), {
      patientUid,
      ...data,
      updatedAt: new Date().toISOString()
    }, { merge: true });
    return { success: true };
  } catch(e) {
    console.log("Error guardando datos clínicos:", e.message);
    return { success: false, error: e.message };
  }
};
export const loadClinicalData = async (patientUid) => {
  try { const snap = await getDoc(doc(db, "patientClinical", patientUid)); return snap.exists() ? snap.data() : null; }
  catch(e) { return null; }
};
export const subscribeClinicalData = (patientUid, callback, onError) => onSnapshot(doc(db, "patientClinical", patientUid), snap => callback(snap.exists() ? snap.data() : null), onError);

// Sube una imagen desde un data URL y devuelve una URL de descarga protegible por Storage Rules.
export const uploadWoundPhoto = async (patientUid, woundId, dataUrl, kind = "evolucion") => {
  try {
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    const fileRef = ref(storage, `woundPhotos/${patientUid}/${woundId}/${kind}-${Date.now()}.jpg`);
    await uploadBytes(fileRef, blob, { contentType: blob.type || "image/jpeg" });
    return { success: true, url: await getDownloadURL(fileRef) };
  } catch(e) {
    console.log("Error subiendo fotografía:", e.message);
    return { success: false, error: e.message };
  }
};

export const registerInviteCode = async (inviteCode, uid) => {
  try { await setDoc(doc(db, "inviteCodes", inviteCode), { uid, createdAt: new Date().toISOString() }); }
  catch(e) { console.log("Error registrando código:", e.message); }
};
export const linkProCarer = async (inviteCode, proUid, proName) => {
  try {
    const snap = await getDoc(doc(db, "inviteCodes", inviteCode));
    if(!snap.exists()) return { success: false, error: "Código no válido" };
    const carerUid = snap.data().uid;
    await setDoc(doc(db, "links", `${proUid}_${carerUid}`), { proUid, proName, carerUid, inviteCode, linkedAt: new Date().toISOString() });
    await setDoc(doc(db, "careTeam", carerUid, "members", proUid), { patientUid: carerUid, professionalUid: proUid, professionalName: proName, role: "profesional", status: "active", permissions: { verConstantes: true, verMedicacion: true, verHeridas: true, verFotografias: false, escribirComentarios: true, descargarFotografias: false }, linkedAt: new Date().toISOString() }, { merge: true });
    await setDoc(doc(db, "userData", carerUid), { isLinkedToPro: true, proUid, proName }, { merge: true });
    return { success: true, carerUid };
  } catch(e) { return { success: false, error: e.message }; }
};

// ── Equipo asistencial y permisos por paciente ──
const careTeamCollection = (patientUid) => collection(db, "careTeam", patientUid, "members");
export const getCareTeam = async (patientUid) => {
  try {
    const snap = await getDocs(careTeamCollection(patientUid));
    return snap.docs.map(d => ({ professionalUid: d.id, ...d.data() }));
  } catch(e) { console.log("Error cargando equipo asistencial:", e.message); return []; }
};
export const getCareTeamMember = async (patientUid, professionalUid) => {
  try { const snap = await getDoc(doc(db, "careTeam", patientUid, "members", professionalUid)); return snap.exists() ? { professionalUid, ...snap.data() } : null; }
  catch(e) { return null; }
};
export const subscribeCareTeam = (patientUid, callback, onError) => onSnapshot(careTeamCollection(patientUid), snap => callback(snap.docs.map(d => ({ professionalUid: d.id, ...d.data() }))), onError);
export const saveCareTeamMember = async (patientUid, professionalUid, memberData) => {
  try {
    await setDoc(doc(db, "careTeam", patientUid, "members", professionalUid), { patientUid, professionalUid, ...memberData, updatedAt: new Date().toISOString() }, { merge: true });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};
export const revokeCareTeamMember = async (patientUid, professionalUid, reason = "Revocado por el paciente") => {
  try {
    await updateDoc(doc(db, "careTeam", patientUid, "members", professionalUid), { status: "revoked", revokedAt: new Date().toISOString(), revokedReason: reason });
    return { success: true };
  } catch(e) { return { success: false, error: e.message }; }
};

export const createPharmacyRequest = async (requestData) => {
  try {
    const ref = await addDoc(collection(db, "pharmacyRequests"), {...requestData, createdAt: new Date().toISOString(), estado: "Pendiente de revisión"});
    return { success: true, id: ref.id };
  } catch(e) { console.log("Error creando solicitud farmacia:", e.message); return { success: false, error: e.message }; }
};
export const getPharmacyRequests = async (pharmacyId) => {
  try {
    const q = query(collection(db, "pharmacyRequests"), where("farmaciaId", "==", pharmacyId));
    const snap = await getDocs(q);
    return snap.docs.map(d => ({id: d.id, ...d.data()}));
  } catch(e) { console.log("Error cargando solicitudes:", e.message); return []; }
};
export const updatePharmacyRequest = async (requestId, updates) => {
  try { await updateDoc(firestoreDoc(db, "pharmacyRequests", requestId), {...updates, updatedAt: new Date().toISOString()}); return { success: true }; }
  catch(e) { return { success: false, error: e.message }; }
};
