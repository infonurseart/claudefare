import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc, getDoc, onSnapshot, collection } from "firebase/firestore";

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

// ── Helpers de sincronización ──

// Guardar datos del cuidador en Firestore
export const saveCarerData = async (userId, data) => {
  try {
    await setDoc(doc(db, "carers", userId), {
      ...data,
      updatedAt: new Date().toISOString()
    }, { merge: true });
  } catch(e) {
    console.log("Error guardando en Firebase:", e.message);
  }
};

// Guardar datos del profesional en Firestore  
export const saveProData = async (userId, data) => {
  try {
    await setDoc(doc(db, "professionals", userId), {
      ...data,
      updatedAt: new Date().toISOString()
    }, { merge: true });
  } catch(e) {
    console.log("Error guardando pro en Firebase:", e.message);
  }
};

// Cargar datos del cuidador
export const loadCarerData = async (userId) => {
  try {
    const snap = await getDoc(doc(db, "carers", userId));
    return snap.exists() ? snap.data() : null;
  } catch(e) {
    console.log("Error cargando de Firebase:", e.message);
    return null;
  }
};

// Escuchar cambios en tiempo real de un cuidador (para el profesional)
export const subscribeToCarerData = (userId, callback) => {
  return onSnapshot(doc(db, "carers", userId), (snap) => {
    if(snap.exists()) callback(snap.data());
  });
};

// Vincular profesional con cuidador
export const linkProCarer = async (inviteCode, proId, proName) => {
  try {
    // Buscar cuidador con ese código
    const snap = await getDoc(doc(db, "inviteCodes", inviteCode));
    if(!snap.exists()) return { success: false, error: "Código no válido" };
    const carerId = snap.data().carerId;
    // Crear vínculo
    await setDoc(doc(db, "links", `${proId}_${carerId}`), {
      proId, proName, carerId,
      inviteCode,
      linkedAt: new Date().toISOString()
    });
    // Marcar cuidador como vinculado
    await setDoc(doc(db, "carers", carerId), { isLinkedToPro: true, proId, proName }, { merge: true });
    return { success: true, carerId };
  } catch(e) {
    return { success: false, error: e.message };
  }
};

// Registrar código de invitación del cuidador
export const registerInviteCode = async (inviteCode, carerId) => {
  try {
    await setDoc(doc(db, "inviteCodes", inviteCode), { carerId, createdAt: new Date().toISOString() });
  } catch(e) {
    console.log("Error registrando código:", e.message);
  }
};
