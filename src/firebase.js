import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc, getDoc, onSnapshot } from "firebase/firestore";
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
export const auth = getAuth(app);

// ── Auth helpers ──
export const registerUser = async (email, password, role, name) => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    // Guardar perfil en Firestore
    await setDoc(doc(db, "users", cred.user.uid), {
      email, role, name,
      createdAt: new Date().toISOString()
    });
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
    const snap = await getDoc(doc(db, "users", cred.user.uid));
    const profile = snap.exists() ? snap.data() : {};
    return { success: true, uid: cred.user.uid, role: profile.role, name: profile.name };
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
  try {
    await sendPasswordResetEmail(auth, email);
    return { success: true };
  } catch(e) {
    return { success: false, error: "No se pudo enviar el correo" };
  }
};

export const onAuthChange = (callback) => onAuthStateChanged(auth, callback);

// ── Firestore helpers ──
export const saveUserData = async (uid, data) => {
  try {
    await setDoc(doc(db, "userData", uid), {
      ...data, updatedAt: new Date().toISOString()
    }, { merge: true });
  } catch(e) { console.log("Error guardando:", e.message); }
};

export const loadUserData = async (uid) => {
  try {
    const snap = await getDoc(doc(db, "userData", uid));
    return snap.exists() ? snap.data() : null;
  } catch(e) { return null; }
};

export const subscribeUserData = (uid, callback) => {
  return onSnapshot(doc(db, "userData", uid), snap => {
    if(snap.exists()) callback(snap.data());
  });
};

export const registerInviteCode = async (inviteCode, uid) => {
  try {
    await setDoc(doc(db, "inviteCodes", inviteCode), {
      uid, createdAt: new Date().toISOString()
    });
  } catch(e) { console.log("Error registrando código:", e.message); }
};

export const linkProCarer = async (inviteCode, proUid, proName) => {
  try {
    const snap = await getDoc(doc(db, "inviteCodes", inviteCode));
    if(!snap.exists()) return { success: false, error: "Código no válido" };
    const carerUid = snap.data().uid;
    await setDoc(doc(db, "links", `${proUid}_${carerUid}`), {
      proUid, proName, carerUid, inviteCode,
      linkedAt: new Date().toISOString()
    });
    await setDoc(doc(db, "userData", carerUid), {
      isLinkedToPro: true, proUid, proName
    }, { merge: true });
    return { success: true, carerUid };
  } catch(e) { return { success: false, error: e.message }; }
};
