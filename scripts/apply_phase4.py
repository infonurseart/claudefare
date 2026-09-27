from pathlib import Path
from textwrap import dedent
from PIL import Image

ROOT = Path('/home/ubuntu/nurseart-fase4/app')
APP = ROOT / 'src' / 'App.jsx'
FIREBASE = ROOT / 'src' / 'firebase.js'
RULES = ROOT / 'firestore.rules'
STORAGE_RULES = ROOT / 'storage.rules'
FUNCTION = ROOT / 'functions' / 'approve-professional.js'
PUBLIC = ROOT / 'public'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


def insert_once(text, marker, addition, label, before=True):
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one marker, found {count}')
    return text.replace(marker, addition + marker if before else marker + addition, 1)


# Firebase client helpers ----------------------------------------------------
firebase = FIREBASE.read_text()
firebase = replace_once(
    firebase,
    'export const createProfessionalRequest = async (uid, data) => {\n  try { await setDoc(doc(db, "professionalRequests", uid), { uid, ...data, status: "pending", requestedAt: new Date().toISOString() }, { merge: true }); return { success: true }; }\n  catch(e) { return { success: false, error: e.message }; }\n};',
    dedent('''\
    export const uploadProfessionalDocument = async (uid, file, kind) => {
      const allowedKinds = ["colegiacion", "identidad"];
      const allowedTypes = ["application/pdf", "image/jpeg", "image/png", "image/webp"];
      try {
        if (!uid || !file) throw new Error("Falta el documento.");
        if (!allowedKinds.includes(kind)) throw new Error("Tipo de documento no válido.");
        if (file.size > 10 * 1024 * 1024) throw new Error("El archivo supera el máximo de 10 MB.");
        if (!allowedTypes.includes(file.type)) throw new Error("Solo se admiten PDF, JPG, PNG o WEBP.");
        const ext = (file.name.split(".").pop() || "bin").toLowerCase().replace(/[^a-z0-9]/g, "");
        const fileRef = ref(storage, `professionalDocuments/${uid}/${kind}-${Date.now()}.${ext}`);
        await uploadBytes(fileRef, file, { contentType: file.type });
        const url = await getDownloadURL(fileRef);
        return {
          success: true,
          document: {
            kind,
            name: file.name.slice(0, 160),
            size: file.size,
            type: file.type,
            path: fileRef.fullPath,
            url,
            uploadedAt: new Date().toISOString()
          }
        };
      } catch (e) {
        return { success: false, error: e.message || "No se pudo subir el documento." };
      }
    };

    export const createProfessionalRequest = async (uid, data) => {
      try {
        const status = ["draft", "submitted"].includes(data?.status) ? data.status : "draft";
        await setDoc(doc(db, "professionalRequests", uid), {
          uid,
          ...data,
          status,
          updatedAt: new Date().toISOString(),
          requestedAt: data?.requestedAt || new Date().toISOString(),
          ...(status === "submitted" ? { submittedAt: new Date().toISOString() } : {})
        }, { merge: true });
        return { success: true };
      } catch(e) { return { success: false, error: e.message }; }
    };'''),
    'professional request helper',
)
FIREBASE.write_text(firebase)

# Cloud Function: only activate accounts with a submitted dossier.
function = FUNCTION.read_text()
function = replace_once(
    function,
    '  const safeData = {',
    dedent('''\
      const requestRef = getFirestore().doc(`professionalRequests/${targetUid}`);
      const verificationRequest = await requestRef.get();
      const requestData = verificationRequest.exists ? verificationRequest.data() : null;
      const documents = Array.isArray(requestData?.documents) ? requestData.documents : [];
      const hasRegistration = documents.some(doc => doc && doc.kind === "colegiacion" && doc.path);
      const hasIdentity = documents.some(doc => doc && doc.kind === "identidad" && doc.path);
      if (!requestData || requestData.status !== "submitted" || !requestData.registrationNumber || !hasRegistration || !hasIdentity) {
        throw new HttpsError("failed-precondition", "La cuenta no ha enviado el expediente profesional completo.");
      }
      const safeData = {'''),
    'approval dossier precondition',
)
function = replace_once(
    function,
    '  await getFirestore().doc(`professionalRequests/${targetUid}`).set({ status: "approved", approvedAt: safeData.approvedAt, approvedBy: request.auth.uid }, { merge: true });',
    '  await requestRef.set({ status: "approved", approvedAt: safeData.approvedAt, approvedBy: request.auth.uid }, { merge: true });',
    'approval request update',
)
FUNCTION.write_text(function)

# Security rules -------------------------------------------------------------
RULES.write_text(dedent('''\
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function signedIn() { return request.auth != null; }
    function owner(uid) { return signedIn() && request.auth.uid == uid; }
    function hasClaim(role) { return signedIn() && request.auth.token.role == role; }
    function hasUserRole(role) {
      return signedIn() &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == role;
    }
    function isAdmin() { return hasClaim('admin'); }
    function isPharmacy() { return hasClaim('farmacia') || hasUserRole('farmacia'); }
    function isApprovedProfessional() {
      return hasClaim('profesional') &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'profesional' &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.verificationStatus == 'approved';
    }
    function activeMember(patientUid, professionalUid) {
      return isApprovedProfessional() && professionalUid == request.auth.uid &&
        exists(/databases/$(database)/documents/careTeam/$(patientUid)/members/$(professionalUid)) &&
        get(/databases/$(database)/documents/careTeam/$(patientUid)/members/$(professionalUid)).data.status == 'active';
    }
    function isAssignedPharmacy(pharmacyId) {
      return isPharmacy() &&
        get(/databases/$(database)/documents/userData/$(request.auth.uid)).data.pharmacyProfile.code == pharmacyId;
    }

    match /users/{uid} {
      allow read: if owner(uid) || isAdmin();
      allow create: if owner(uid) &&
        request.resource.data.role in ['pendiente_verificacion', 'farmacia', 'cuidador'] &&
        request.resource.data.verificationStatus in ['pending', 'not_required'];
      allow update: if owner(uid) &&
        request.resource.data.role == resource.data.role &&
        request.resource.data.verificationStatus == resource.data.verificationStatus;
      allow delete: if false;
    }

    match /userData/{uid} {
      allow read, create, update: if owner(uid);
      allow delete: if false;
    }

    match /professionalRequests/{uid} {
      allow create: if owner(uid) && request.resource.data.uid == uid &&
        request.resource.data.status in ['draft', 'submitted'];
      allow update: if owner(uid) && request.resource.data.uid == uid &&
        request.resource.data.status in ['draft', 'submitted'];
      allow read: if owner(uid) || isAdmin();
      allow delete: if false;
    }

    match /patientClinical/{patientUid} {
      allow read: if owner(patientUid) || activeMember(patientUid, request.auth.uid);
      allow create: if owner(patientUid) && request.resource.data.patientUid == patientUid;
      allow update: if owner(patientUid) || activeMember(patientUid, request.auth.uid);
      allow delete: if false;
    }

    match /careTeam/{patientUid}/members/{professionalUid} {
      allow get: if owner(patientUid) || (isApprovedProfessional() && request.auth.uid == professionalUid);
      allow list: if owner(patientUid);
      allow create: if owner(patientUid) ||
        (isApprovedProfessional() && request.auth.uid == professionalUid && request.resource.data.status == 'active');
      allow update: if owner(patientUid) || (isApprovedProfessional() && request.auth.uid == professionalUid);
      allow delete: if false;
    }

    match /inviteCodes/{code} {
      allow get: if signedIn();
      allow list: if false;
      allow create: if owner(request.resource.data.uid);
      allow update, delete: if false;
    }

    match /links/{linkId} {
      allow get: if signedIn() && (resource.data.proUid == request.auth.uid || resource.data.carerUid == request.auth.uid);
      allow list: if false;
      allow create: if isApprovedProfessional() && request.resource.data.proUid == request.auth.uid &&
        linkId == request.auth.uid + '_' + request.resource.data.carerUid;
      allow update, delete: if false;
    }

    match /pharmacyRequests/{reqId} {
      allow create: if owner(request.resource.data.carerUid);
      allow read: if signedIn() &&
        (resource.data.carerUid == request.auth.uid || isAssignedPharmacy(resource.data.farmaciaId));
      allow update: if signedIn() &&
        (resource.data.carerUid == request.auth.uid || isAssignedPharmacy(resource.data.farmaciaId));
      allow delete: if false;
    }
  }
}
'''))

STORAGE_RULES.write_text(dedent('''\
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    function signedIn() { return request.auth != null; }
    function isAdmin() { return signedIn() && request.auth.token.role == 'admin'; }
    function isApprovedProfessional(patientUid) {
      return signedIn() && request.auth.token.role == 'profesional' &&
        firestore.get(/databases/(default)/documents/users/$(request.auth.uid)).data.verificationStatus == 'approved' &&
        firestore.get(/databases/(default)/documents/careTeam/$(patientUid)/members/$(request.auth.uid)).data.status == 'active';
    }

    match /woundPhotos/{patientUid}/{woundId}/{fileName} {
      allow read: if signedIn() && (
        request.auth.uid == patientUid ||
        (isApprovedProfessional(patientUid) &&
          firestore.get(/databases/(default)/documents/careTeam/$(patientUid)/members/$(request.auth.uid)).data.permissions.verFotografias == true)
      );
      allow write: if signedIn() && request.auth.uid == patientUid &&
        request.resource.size < 5 * 1024 * 1024 && request.resource.contentType.matches('image/.*');
      allow delete: if false;
    }

    match /professionalDocuments/{uid}/{fileName} {
      allow read: if signedIn() && (request.auth.uid == uid || isAdmin());
      allow write: if signedIn() && request.auth.uid == uid &&
        request.resource.size < 10 * 1024 * 1024 &&
        request.resource.contentType.matches('(application/pdf|image/jpeg|image/png|image/webp)');
      allow delete: if false;
    }
  }
}
'''))

# App implementation --------------------------------------------------------
app = APP.read_text()
app = replace_once(
    app,
    'createProfessionalRequest,getProfessionalRequests,approveProfessionalAccount,rejectProfessionalAccount}from"./firebase.js";',
    'createProfessionalRequest,getProfessionalRequests,approveProfessionalAccount,rejectProfessionalAccount,uploadProfessionalDocument}from"./firebase.js";',
    'firebase helper import',
)
app = replace_once(
    app,
    'const [registerForm,setRegisterForm]=useState({name:"",surname:"",email:"",pass:"",pass2:""});',
    'const [registerForm,setRegisterForm]=useState({name:"",surname:"",email:"",pass:"",pass2:"",pharmacyCode:""});',
    'registration state',
)
app = replace_once(
    app,
    'const [pacProfile,setPacProfile]=useState({name:"María",surname:"García",email:"maria@email.es",avatar:"👵"});',
    'const [pacProfile,setPacProfile]=useState({name:"María",surname:"García",email:"maria@email.es",avatar:"👵"});\n  const [pharmacyProfile,setPharmacyProfile]=useState({name:"",code:""});',
    'pharmacy profile state',
)
app = replace_once(
    app,
    'const [professionalRequests,setProfessionalRequests]=useState([]);',
    dedent('''\
    const [professionalRequests,setProfessionalRequests]=useState([]);
    const [proVerification,setProVerification]=useState({professionalType:"Enfermería",registrationNumber:"",province:"",documents:[],declarationAccepted:false,submittedAt:null});
    const [proVerificationUploading,setProVerificationUploading]=useState("");
    const [pharmacyOrders,setPharmacyOrders]=useState([]);
    const [deferredInstallPrompt,setDeferredInstallPrompt]=useState(null);
    const [pwaInstalled,setPwaInstalled]=useState(false);''').rstrip(),
    'phase four states',
)
app = replace_once(
    app,
    '          if(data.umbralDias) setUmbralDias(data.umbralDias);',
    dedent('''\
              if(data.umbralDias) setUmbralDias(data.umbralDias);
              if(data.proVerification) setProVerification(p=>({...p,...data.proVerification}));
              if(data.pharmacyProfile) setPharmacyProfile(data.pharmacyProfile);
              if(data.pacCart) setPacCart(data.pacCart);
              if(data.pharmacyOrders) setPharmacyOrders(data.pharmacyOrders);''').rstrip(),
    'authenticated phase four load',
)
app = replace_once(
    app,
    '          if(d.umbralDias) setUmbralDias(d.umbralDias);',
    dedent('''\
              if(d.umbralDias) setUmbralDias(d.umbralDias);
              if(d.proVerification) setProVerification(p=>({...p,...d.proVerification}));
              if(d.pharmacyProfile) setPharmacyProfile(d.pharmacyProfile);
              if(d.pacCart) setPacCart(d.pacCart);
              if(d.pharmacyOrders) setPharmacyOrders(d.pharmacyOrders);''').rstrip(),
    'local phase four load',
)
app = replace_once(
    app,
    'const data={pacMeds,medHistory,vitHist,balHist,higHist,sintHist,solicitudes,farmacia,consentFarmacia:consentFarmacia||null,umbralDias,pacProfile,proProfile,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,chatMsgs};',
    'const data={pacMeds,medHistory,vitHist,balHist,higHist,sintHist,solicitudes,farmacia,consentFarmacia:consentFarmacia||null,umbralDias,pacProfile,proProfile,pharmacyProfile,proVerification,pacCart,pharmacyOrders,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,chatMsgs};',
    'phase four local persistence',
)
app = replace_once(
    app,
    'await saveUserData(authUser.uid,{pacMeds,medHistory,vitHist,balHist,higHist,sintHist,pacProfile,proProfile,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,role,solicitudes,farmacia,umbralDias,consentFarmacia:consentFarmacia||null});',
    'await saveUserData(authUser.uid,{pacMeds,medHistory,vitHist,balHist,higHist,sintHist,pacProfile,proProfile,pharmacyProfile,proVerification,pacCart,pharmacyOrders,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,role,solicitudes,farmacia,umbralDias,consentFarmacia:consentFarmacia||null});',
    'phase four firebase persistence',
)
app = replace_once(
    app,
    '},[pacMeds,medHistory,vitHist,balHist,higHist,sintHist,heridas,solicitudes,farmacia,consentFarmacia,umbralDias,pacProfile,proProfile,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,chatMsgs]);',
    '},[pacMeds,medHistory,vitHist,balHist,higHist,sintHist,heridas,solicitudes,farmacia,consentFarmacia,umbralDias,pacProfile,proProfile,pharmacyProfile,proVerification,pacCart,pharmacyOrders,dark,easyMode,isLinkedToPro,recomendaciones,sugerencias,chatMsgs]);',
    'phase four persistence dependencies',
)
app = insert_once(
    app,
    '  // ── Firebase Auth listener ──',
    dedent('''\
      // ── PWA install prompt ──
      useEffect(()=>{
        const onBeforeInstallPrompt=(event)=>{event.preventDefault();setDeferredInstallPrompt(event);};
        const onInstalled=()=>{setPwaInstalled(true);setDeferredInstallPrompt(null);showToast("✓ NurseArt ya está instalada en este dispositivo");};
        window.addEventListener("beforeinstallprompt",onBeforeInstallPrompt);
        window.addEventListener("appinstalled",onInstalled);
        return()=>{window.removeEventListener("beforeinstallprompt",onBeforeInstallPrompt);window.removeEventListener("appinstalled",onInstalled);};
      },[]);

    '''),
    'PWA event listeners',
)
app = insert_once(
    app,
    '  useEffect(()=>{\n    if(role!=="admin"||screen!=="admin-home")return;',
    dedent('''\
      useEffect(()=>{
        if(role!=="farmacia"||screen!=="farmacia-home"||!pharmacyProfile.code)return;
        getPharmacyRequests(pharmacyProfile.code).then(data=>{if(data.length)setSolicitudes(data);});
      },[role,screen,pharmacyProfile.code]);

    '''),
    'pharmacy request loader',
)
app = replace_once(
    app,
    '  const go=s=>{setScreen(s);setModal(null);};',
    dedent('''\
      const professionalAccessActive=role!=="pro"||roleStatus==="approved";
      const installNurseArt=async()=>{
        if(!deferredInstallPrompt){showToast("Usa \"Añadir a pantalla de inicio\" desde el menú de tu navegador.");return;}
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice;
        setDeferredInstallPrompt(null);
      };
      const go=s=>{
        const protectedProfessionalScreens=["home","panel","learn","store","pro-profile"];
        if(role==="pro"&&!professionalAccessActive&&protectedProfessionalScreens.includes(s)){
          setScreen("pro-verification");setModal(null);return;
        }
        setScreen(s);setModal(null);
      };''').rstrip(),
    'professional access guard',
)
app = replace_once(
    app,
    '  const linkPatient=async code=>{\n    // Intentar vincular via Firebase primero',
    '  const linkPatient=async code=>{\n    if(role==="pro"&&!professionalAccessActive){showToast("⚠ Completa y activa tu verificación antes de vincular pacientes");go("pro-verification");return;}\n    // Intentar vincular via Firebase primero',
    'linking access guard',
)
app = replace_once(
    app,
    '  const pacCartCount=Object.values(pacCart).reduce((a,b)=>a+b.qty,0);',
    dedent('''\
      const pacCartCount=Object.values(pacCart).reduce((a,b)=>a+b.qty,0);
      const pacCartTotal=Object.values(pacCart).reduce((a,b)=>a+b.qty*b.price,0);
      const addPacToCart=product=>{
        setPacCart(prev=>({...prev,[product.n]:{qty:(prev[product.n]?.qty||0)+1,price:product.p,icon:product.e||"💊",category:product.cat||"Parafarmacia"}}));
        showToast(`✓ ${product.n} añadido al pedido`);
      };
      const updatePacCartQty=(name,delta)=>setPacCart(prev=>{
        const current=prev[name];if(!current)return prev;
        const qty=current.qty+delta;
        if(qty<=0){const next={...prev};delete next[name];return next;}
        return {...prev,[name]:{...current,qty}};
      });
      const submitPharmacyCart=async()=>{
        if(!Object.keys(pacCart).length){showToast("El carrito está vacío");return;}
        if(farmacia.estado!=="vinculada"||!farmacia.codigo){setModal(null);go("pac-farmacia");showToast("🔗 Vincula una farmacia e introduce su código antes de enviar el pedido");return;}
        const items=Object.entries(pacCart).map(([name,item])=>({name,quantity:item.qty,unitPrice:item.price,icon:item.icon,category:item.category}));
        const order={
          id:`order-${Date.now()}`,type:"store_order",title:"Pedido de parafarmacia",items,total:Number(pacCartTotal.toFixed(2)),
          paciente:`${pacProfile.name} ${pacProfile.surname||""}`.trim(),carerUid:authUser?.uid||null,
          farmacia:farmacia.nombre,farmaciaId:farmacia.codigo,fechaCreacion:new Date().toLocaleString("es-ES"),
          estado:"Pendiente de revisión",historial:[{fecha:new Date().toLocaleString("es-ES"),accion:"Pedido de parafarmacia enviado por cuidador",usuario:pacProfile.name}]
        };
        setPharmacyOrders(prev=>[order,...prev]);setPacCart({});setModal(null);
        if(authUser){const result=await createPharmacyRequest(order);if(!result.success){showToast("⚠ Pedido guardado en el dispositivo; se reintentará al recuperar conexión");return;}}
        showToast("✓ Pedido enviado a la farmacia para su revisión");
      };''').rstrip(),
    'pharmacy cart helpers',
)
# Registration and login flows
app = replace_once(
    app,
    'await createProfessionalRequest(r.uid,{name:profile.name,surname:profile.surname,email:profile.email,requestedRole:"profesional"});go("home");',
    'await createProfessionalRequest(r.uid,{name:profile.name,surname:profile.surname,email:profile.email,requestedRole:"profesional",status:"draft"});go("pro-verification");',
    'professional registration redirect',
)
app = replace_once(
    app,
    'if(r.success){setRole("pro");setRoleStatus(r.roleStatus||"active");setProProfile({name:r.name||"Profesional",surname:"",email:r.email||loginProForm.email,role:"Enfermera/o",avatar:"👩‍⚕️"});go("home");}else{setAuthError(r.error);}',
    'if(r.success){const approved=r.roleStatus==="approved";setRole("pro");setRoleStatus(r.roleStatus||"pending");setProProfile({name:r.name||"Profesional",surname:"",email:r.email||loginProForm.email,role:"Enfermera/o",avatar:"👩‍⚕️"});go(approved?"home":"pro-verification");}else{setAuthError(r.error);}',
    'professional login redirect',
)
app = replace_once(
    app,
    '<div style={S.inp}><span>🏥</span><input style={S.inpEl} placeholder="Farmacia Central..." value={registerForm.name} onChange={e=>setRegisterForm(f=>({...f,name:e.target.value}))}/></div>',
    dedent('''\
              <div style={S.inp}><span>🏥</span><input style={S.inpEl} placeholder="Farmacia Central..." value={registerForm.name} onChange={e=>setRegisterForm(f=>({...f,name:e.target.value}))}/></div>
              <p style={{fontSize:11,fontWeight:700,color:D.t2,marginBottom:5}}>Código del establecimiento</p>
              <div style={S.inp}><span>🔑</span><input style={S.inpEl} placeholder="Ej. FARMACIA-CENTRAL" value={registerForm.pharmacyCode} onChange={e=>setRegisterForm(f=>({...f,pharmacyCode:e.target.value.toUpperCase()}))}/></div>''').rstrip(),
    'pharmacy registration code field',
)
app = replace_once(
    app,
    'if(r.success){setRole("farmacia");setProProfile({name:registerForm.name||"Farmacia",email:loginProForm.email,avatar:"🏥"});go("farmacia-home");}else{setAuthError(r.error);}',
    'if(r.success){const profile={name:registerForm.name||"Farmacia",code:registerForm.pharmacyCode.trim().toUpperCase()};setRole("farmacia");setPharmacyProfile(profile);setProProfile({name:profile.name,email:loginProForm.email,avatar:"🏥"});await saveUserData(r.uid,{pharmacyProfile:profile});go("farmacia-home");}else{setAuthError(r.error);}',
    'pharmacy registration persistence',
)
app = replace_once(
    app,
    'if(r.success){setRole("farmacia");setProProfile({name:r.name||"Farmacia",email:loginProForm.email,avatar:"🏥"});go("farmacia-home");}else{setAuthError(r.error);}',
    'if(r.success){const saved=await loadUserData(r.uid);const profile=saved?.pharmacyProfile||{name:r.name||"Farmacia",code:""};setRole("farmacia");setPharmacyProfile(profile);setProProfile({name:profile.name||r.name||"Farmacia",email:loginProForm.email,avatar:"🏥"});go("farmacia-home");}else{setAuthError(r.error);}',
    'pharmacy login load',
)
# Professional verification screen
verification_ui = dedent('''\
  {/* ══ VERIFICACIÓN PROFESIONAL ══ */}
  {screen==="pro-verification"&&(
    <div style={S.sc}>
      <Grad grad="linear-gradient(150deg,#1e3a8a,#2563EB 60%,#0284c7)">
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
          <div><p style={{fontSize:11,color:"rgba(255,255,255,.72)",fontWeight:700}}>ACCESO PROFESIONAL</p><h2 style={{fontSize:20,fontWeight:900,color:"#fff",marginTop:3}}>Verificación de identidad</h2><p style={{fontSize:11,color:"rgba(255,255,255,.78)",marginTop:4}}>Completa el expediente para habilitar funciones clínicas.</p></div>
          <div style={{width:46,height:46,borderRadius:14,background:"rgba(255,255,255,.16)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:24}}>🛡️</div>
        </div>
      </Grad>
      <div style={S.scr}>
        {roleStatus==="approved"?(
          <div style={{...S.card,background:D.greenBg,border:`1.5px solid ${D.green}55`,marginBottom:14}}><p style={{fontSize:14,fontWeight:900,color:D.green}}>✓ Cuenta profesional activa</p><p style={{fontSize:11,color:D.t2,marginTop:5,lineHeight:1.5}}>Tu documentación ha sido revisada. Puedes acceder al panel clínico y vincular pacientes.</p><button style={{...S.btn(D.blue),borderRadius:11,marginTop:12}} onClick={()=>go("home")}>Ir a mi panel →</button></div>
        ):(
          <>
            <div style={{...S.card,background:roleStatus==="rejected"?D.redBg:D.amberBg,border:`1px solid ${roleStatus==="rejected"?D.red:D.amber}55`,marginBottom:14}}>
              <p style={{fontSize:13,fontWeight:900,color:roleStatus==="rejected"?D.red:D.amber}}>{roleStatus==="rejected"?"⚠ Requiere una nueva presentación":"⏳ Cuenta sin activar"}</p>
              <p style={{fontSize:11,color:D.t2,lineHeight:1.55,marginTop:5}}>Hasta que un administrador valide tu identidad profesional, no podrás ver datos clínicos, vincular pacientes ni usar las funciones profesionales.</p>
            </div>
            <div style={{...S.card,marginBottom:14}}>
              <p style={{fontSize:13,fontWeight:900,color:D.t,marginBottom:4}}>1. Datos de colegiación</p><p style={{fontSize:10,color:D.t2,marginBottom:12}}>Introduce los datos tal como figuran en tu acreditación profesional.</p>
              <p style={{fontSize:11,fontWeight:700,color:D.t2,marginBottom:5}}>Profesión</p>
              <select style={{...S.inpEl,background:D.inp,border:`1px solid ${D.border}`,padding:"11px 12px",borderRadius:10,width:"100%",marginBottom:10}} value={proVerification.professionalType} onChange={e=>setProVerification(p=>({...p,professionalType:e.target.value}))}>{["Enfermería","Medicina","Fisioterapia","Farmacia","Terapia ocupacional","Otra profesión sanitaria"].map(option=><option key={option}>{option}</option>)}</select>
              <p style={{fontSize:11,fontWeight:700,color:D.t2,marginBottom:5}}>Número de colegiación</p>
              <div style={S.inp}><span>🪪</span><input style={S.inpEl} placeholder="Ej. 28-12345" value={proVerification.registrationNumber} onChange={e=>setProVerification(p=>({...p,registrationNumber:e.target.value.toUpperCase()}))}/></div>
              <p style={{fontSize:11,fontWeight:700,color:D.t2,marginBottom:5}}>Provincia o colegio profesional</p>
              <div style={S.inp}><span>📍</span><input style={S.inpEl} placeholder="Ej. Colegio Oficial de Enfermería de Madrid" value={proVerification.province} onChange={e=>setProVerification(p=>({...p,province:e.target.value}))}/></div>
            </div>
            <div style={{...S.card,marginBottom:14}}>
              <p style={{fontSize:13,fontWeight:900,color:D.t,marginBottom:4}}>2. Documentación obligatoria</p><p style={{fontSize:10,color:D.t2,lineHeight:1.5,marginBottom:12}}>Sube un PDF o imagen (JPG, PNG o WEBP), hasta 10 MB por archivo. Los documentos solo serán visibles por ti y por el administrador revisor.</p>
              {[{kind:"colegiacion",title:"Acreditación de colegiación",detail:"Certificado, carné colegial o acreditación equivalente."},{kind:"identidad",title:"Documento identificativo",detail:"Documento de identidad o acreditación profesional con nombre visible."}].map(item=>{
                const document=proVerification.documents?.find(doc=>doc.kind===item.kind);
                const isUploading=proVerificationUploading===item.kind;
                return <div key={item.kind} style={{background:document?D.greenBg:D.inp,border:`1px dashed ${document?D.green:D.border}`,borderRadius:12,padding:"11px 12px",marginBottom:9}}>
                  <div style={{display:"flex",alignItems:"center",gap:9}}><span style={{fontSize:20}}>{document?"✓":"📄"}</span><div style={{flex:1}}><p style={{fontSize:12,fontWeight:800,color:D.t}}>{item.title}</p><p style={{fontSize:10,color:D.t2,marginTop:2}}>{document?`${document.name} · ${(document.size/1024/1024).toFixed(1)} MB`:item.detail}</p></div>{document&&<button onClick={()=>setProVerification(p=>({...p,documents:p.documents.filter(doc=>doc.kind!==item.kind)}))} style={{border:"none",background:"transparent",color:D.red,fontWeight:800,cursor:"pointer"}}>Quitar</button>}</div>
                  <label htmlFor={`pro-document-${item.kind}`} style={{...S.btnG,display:"block",textAlign:"center",padding:"8px 10px",marginTop:9,borderColor:D.blue,color:D.blue,fontSize:11,cursor:isUploading?"wait":"pointer",opacity:isUploading?.65:1}}>{isUploading?"Subiendo…":document?"Sustituir archivo":"Seleccionar archivo"}</label>
                  <input id={`pro-document-${item.kind}`} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" style={{display:"none"}} onChange={async event=>{const file=event.target.files?.[0];if(!file||!authUser)return;setProVerificationUploading(item.kind);const result=await uploadProfessionalDocument(authUser.uid,file,item.kind);setProVerificationUploading("");event.target.value="";if(!result.success){showToast(`⚠ ${result.error}`);return;}setProVerification(p=>({...p,documents:[...(p.documents||[]).filter(doc=>doc.kind!==item.kind),result.document]}));showToast("✓ Documento protegido y subido");}}/>
                </div>;
              })}
            </div>
            <label style={{...S.card,display:"flex",gap:10,alignItems:"flex-start",marginBottom:12,cursor:"pointer"}}><input type="checkbox" checked={proVerification.declarationAccepted} onChange={e=>setProVerification(p=>({...p,declarationAccepted:e.target.checked}))} style={{marginTop:3,accentColor:D.blue}}/><span style={{fontSize:10,color:D.t2,lineHeight:1.55}}>Declaro que los datos y documentos aportados son veraces y autorizo su revisión exclusivamente para activar mi cuenta profesional.</span></label>
            <button style={{...S.btn(D.blue),borderRadius:12,marginBottom:8,opacity:proVerificationUploading?.65:1}} disabled={!!proVerificationUploading} onClick={async()=>{const docs=proVerification.documents||[];if(!authUser){showToast("⚠ Inicia sesión para enviar el expediente");return;}if(!proVerification.registrationNumber.trim()||!proVerification.province.trim()){showToast("⚠ Completa tus datos de colegiación");return;}if(!docs.some(doc=>doc.kind==="colegiacion")||!docs.some(doc=>doc.kind==="identidad")){showToast("⚠ Sube los dos documentos requeridos");return;}if(!proVerification.declarationAccepted){showToast("⚠ Debes aceptar la declaración de veracidad");return;}const payload={name:proProfile.name,surname:proProfile.surname||"",email:proProfile.email,requestedRole:"profesional",professionalType:proVerification.professionalType,registrationNumber:proVerification.registrationNumber.trim(),province:proVerification.province.trim(),documents:docs,declarationAccepted:true,status:"submitted"};const result=await createProfessionalRequest(authUser.uid,payload);if(result.success){setProVerification(p=>({...p,submittedAt:new Date().toISOString()}));setRoleStatus("pending");showToast("✓ Expediente enviado para revisión");}else showToast(`⚠ ${result.error}`);}}>Enviar expediente para revisión</button>
            <button style={{...S.btnG,borderRadius:12}} onClick={async()=>{if(!authUser){showToast("⚠ Inicia sesión para guardar");return;}const result=await createProfessionalRequest(authUser.uid,{name:proProfile.name,surname:proProfile.surname||"",email:proProfile.email,requestedRole:"profesional",professionalType:proVerification.professionalType,registrationNumber:proVerification.registrationNumber.trim(),province:proVerification.province.trim(),documents:proVerification.documents||[],status:"draft"});showToast(result.success?"✓ Borrador guardado":"⚠ No se pudo guardar el borrador");}}>Guardar borrador</button>
          </>
        )}
        {deferredInstallPrompt&&!pwaInstalled&&<button style={{...S.btnG,borderRadius:12,marginTop:14,borderColor:D.blue,color:D.blue}} onClick={installNurseArt}>📲 Instalar NurseArt en este móvil</button>}
      </div>
    </div>
  )}

''')
app = insert_once(app, '  {/* ══ PRO HOME ══ */}', verification_ui, 'professional verification screen')
# Add access to verification from the regular professional profile.
app = replace_once(
    app,
    '[{e:"🔔",t:"Notificaciones",s:"3 pendientes",fn:()=>setModal("pro-notifs")},{e:"🏅",t:"Mis certificados",s:"2 obtenidos",fn:()=>setModal("pro-certs")},{e:"✏️",t:"Editar perfil",s:"Nombre, correo y rol",fn:()=>setModal("pro-edit")},{e:"⚙️",t:"Configuración",s:"Preferencias",fn:()=>setModal("pro-config")}].map',
    '[{e:"🛡️",t:"Verificación profesional",s:roleStatus==="approved"?"Cuenta activa":"Completar expediente",fn:()=>go("pro-verification")},{e:"🔔",t:"Notificaciones",s:"3 pendientes",fn:()=>setModal("pro-notifs")},{e:"🏅",t:"Mis certificados",s:"2 obtenidos",fn:()=>setModal("pro-certs")},{e:"✏️",t:"Editar perfil",s:"Nombre, correo y rol",fn:()=>setModal("pro-edit")},{e:"⚙️",t:"Configuración",s:"Preferencias",fn:()=>setModal("pro-config")}].map',
    'professional profile verification navigation',
)
# Store and pharmacy UX.
app = replace_once(app, '<div><h2 style={{fontSize:18,fontWeight:900,color:"#fff"}}>Tienda</h2></div>', '<div><h2 style={{fontSize:18,fontWeight:900,color:"#fff"}}>Tienda de farmacia</h2><p style={{fontSize:10,color:"rgba(255,255,255,.72)",marginTop:2}}>Parafarmacia · pedido para revisión</p></div>', 'store title')
pac_store_start = app.index('  {/* ══ PAC STORE ══ */}')
app_prefix, pac_store_body = app[:pac_store_start], app[pac_store_start:]
pac_store_body = replace_once(
    pac_store_body,
    '      <div style={S.scr}>\n        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>',
    dedent('''\
          <div style={S.scr}>
            <div style={{...S.card,background:D.blueBg,border:`1px solid ${D.blue}33`,padding:"10px 12px",marginBottom:12}}><p style={{fontSize:11,fontWeight:800,color:D.blue}}>🛡️ Pedido seguro a farmacia</p><p style={{fontSize:10,color:D.t2,lineHeight:1.45,marginTop:3}}>El carrito crea una solicitud de preparación. No hay cobro online ni se incluyen medicamentos sujetos a receta.</p></div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>''').rstrip(),
    'store safety card',
)
app = app_prefix + pac_store_body
app = replace_once(
    app,
    'onClick={()=>{setPacCart(prev=>({...prev,[p.n]:{qty:(prev[p.n]?.qty||0)+1,price:p.p}}));showToast(`✓ ${p.n} añadido`);}}',
    'onClick={()=>addPacToCart(p)}',
    'patient store add to cart',
)
orders_section = dedent('''\
        {/* Pedidos de parafarmacia */}
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10,marginTop:16}}><p style={{fontSize:13,fontWeight:800,color:D.t}}>🛒 Pedidos de parafarmacia</p><span style={pill(D.purpleBg,D.purple)}>{pharmacyOrders.length}</span></div>
        {pharmacyOrders.length===0?<div style={{...S.card,textAlign:"center",padding:"18px 14px",marginBottom:14}}><p style={{fontSize:11,color:D.t2}}>Aún no hay pedidos de productos de parafarmacia.</p><button style={{...S.btn("#059669"),borderRadius:9,fontSize:11,marginTop:9}} onClick={()=>go("pac-store")}>Ir a la tienda →</button></div>:pharmacyOrders.slice(0,4).map(order=><div key={order.id} style={{...S.card,marginBottom:8,border:`1px solid ${D.purple}33`}}><div style={{display:"flex",justifyContent:"space-between",gap:8}}><div><p style={{fontSize:12,fontWeight:800,color:D.t}}>Pedido · {order.items?.length||0} producto{(order.items?.length||0)!==1?"s":""}</p><p style={{fontSize:10,color:D.t2,marginTop:3}}>{order.farmacia} · €{Number(order.total||0).toFixed(2)}</p></div><span style={pill(D.purpleBg,D.purple)}>{order.estado}</span></div><p style={{fontSize:9,color:D.t3,marginTop:6}}>{order.fechaCreacion}</p></div>)}

''')
app = insert_once(app, '        {/* Historial de solicitudes */}', orders_section, 'patient pharmacy orders section')
farmacia_home_start = app.index('  {/* ══ FARMACIA HOME ══ */}')
app_prefix, farmacia_home_body = app[:farmacia_home_start], app[farmacia_home_start:]
farmacia_home_body = farmacia_home_body.replace('<p style={{fontSize:13,fontWeight:800,color:D.t,marginBottom:10}}>📋 Solicitudes de reposición</p>', '<p style={{fontSize:13,fontWeight:800,color:D.t,marginBottom:10}}>📋 Solicitudes y pedidos</p>\n        {!pharmacyProfile.code&&<div style={{...S.card,background:D.amberBg,border:`1px solid ${D.amber}55`,marginBottom:12}}><p style={{fontSize:12,fontWeight:800,color:D.amber,marginBottom:6}}>Configura el código de tu establecimiento</p><p style={{fontSize:10,color:D.t2,marginBottom:8}}>Comparte este mismo código con tus pacientes para recibir sus pedidos.</p><div style={S.inp}><span>🔑</span><input style={S.inpEl} placeholder="Ej. FARMACIA-CENTRAL" value={pharmacyProfile.code||""} onChange={e=>setPharmacyProfile(p=>({...p,code:e.target.value.toUpperCase()}))}/></div></div>}', 1)
app = app_prefix + farmacia_home_body
app = replace_once(app, '<p style={{fontSize:11,color:"rgba(255,255,255,.7)"}}>Portal farmacia — piloto</p>', '<p style={{fontSize:11,color:"rgba(255,255,255,.7)"}}>Portal farmacia · {pharmacyProfile.code||"sin código configurado"}</p>', 'pharmacy header code')
app = replace_once(app, '<p style={{fontSize:12,color:D.t2}}>Cuando los pacientes vinculados soliciten reposición aparecerán aquí.</p>', '<p style={{fontSize:12,color:D.t2}}>Las reposiciones y los pedidos de parafarmacia con tu código aparecerán aquí.</p>', 'pharmacy empty state')
app = replace_once(app, '<p style={{fontSize:13,fontWeight:800,color:D.t}}>{s.med}</p>', '<p style={{fontSize:13,fontWeight:800,color:D.t}}>{s.type==="store_order"?`Pedido de parafarmacia · ${s.items?.length||0} productos`:s.med}</p>', 'pharmacy request title')
app = replace_once(app, '<p style={{fontSize:10,color:D.t3}}>CN: {s.cn} · {s.presentacion}</p>', '<p style={{fontSize:10,color:D.t3}}>{s.type==="store_order"?(s.items||[]).map(item=>`${item.name} ×${item.quantity}`).join(" · "):`CN: ${s.cn} · ${s.presentacion}`}</p>', 'pharmacy request detail')
app = replace_once(app, '<p style={{fontSize:10,color:D.t2}}>📦 {s.stockEstimado} uds · {s.pauta}</p>', '<p style={{fontSize:10,color:D.t2}}>{s.type==="store_order"?`🛒 Total estimado: €${Number(s.total||0).toFixed(2)}`:`📦 ${s.stockEstimado} uds · ${s.pauta}`}</p>', 'pharmacy request amount')
# Insert pharmacy cart modal before professional cart modal.
cart_modal = dedent('''\
  {/* Modal carrito de farmacia */}
  {modal==="pac-cart"&&(
    <div style={{position:"absolute",top:0,left:0,right:0,bottom:0,background:"rgba(15,23,42,.6)",display:"flex",alignItems:"flex-end",zIndex:500}} onClick={e=>e.target===e.currentTarget&&setModal(null)}>
      <div style={{background:D.card,borderRadius:"20px 20px 0 0",padding:20,width:"100%",maxHeight:"84%",overflowY:"auto"}}>
        <div style={{width:32,height:4,background:D.border,borderRadius:4,margin:"0 auto 14px"}}/>
        <div style={{display:"flex",justifyContent:"space-between",gap:10,marginBottom:8}}><div><p style={{fontSize:16,fontWeight:900,color:D.t}}>🛒 Carrito de farmacia</p><p style={{fontSize:10,color:D.t2,marginTop:3}}>Solicitud de preparación; sin pago online.</p></div><span style={pill(D.greenBg,D.green)}>{pacCartCount} uds.</span></div>
        {Object.keys(pacCart).length===0?<div style={{textAlign:"center",padding:"28px 12px"}}><p style={{fontSize:32}}>🧺</p><p style={{fontSize:12,color:D.t2,marginTop:8}}>Aún no has añadido productos.</p><button style={{...S.btn("#059669"),borderRadius:10,fontSize:12,marginTop:12}} onClick={()=>{setModal(null);go("pac-store")}}>Ver productos →</button></div>:(<>
          {Object.entries(pacCart).map(([name,item])=><div key={name} style={{...S.row,marginBottom:8}}><div style={{fontSize:21}}>{item.icon||"💊"}</div><div style={{flex:1}}><p style={{fontSize:12,fontWeight:800,color:D.t}}>{name}</p><p style={{fontSize:10,color:D.t2}}>€{Number(item.price).toFixed(2)} · {item.category||"Parafarmacia"}</p></div><div style={{display:"flex",alignItems:"center",gap:6}}><button onClick={()=>updatePacCartQty(name,-1)} style={{width:25,height:25,borderRadius:8,border:`1px solid ${D.border}`,background:D.inp,color:D.t,fontWeight:900,cursor:"pointer"}}>−</button><span style={{fontSize:12,fontWeight:800,color:D.t,minWidth:14,textAlign:"center"}}>{item.qty}</span><button onClick={()=>updatePacCartQty(name,1)} style={{width:25,height:25,borderRadius:8,border:"none",background:"#059669",color:"#fff",fontWeight:900,cursor:"pointer"}}>+</button></div></div>)}
          <div style={{borderTop:`1px solid ${D.border}`,paddingTop:12,marginTop:10}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}><p style={{fontSize:13,fontWeight:800,color:D.t}}>Total estimado</p><p style={{fontSize:19,fontWeight:900,color:"#059669"}}>€{pacCartTotal.toFixed(2)}</p></div><p style={{fontSize:10,color:D.t3,lineHeight:1.45,marginBottom:12}}>La farmacia confirmará disponibilidad y precio final antes de cualquier cobro o recogida.</p><button style={{...S.btn("#059669"),borderRadius:12}} onClick={submitPharmacyCart}>Enviar pedido para revisión</button></div>
        </>)}
        <button style={{...S.btnG,borderRadius:12,marginTop:8}} onClick={()=>setModal(null)}>Cerrar</button>
      </div>
    </div>
  )}

''')
app = insert_once(app, '  {/* Modal carrito pro */}', cart_modal, 'patient pharmacy cart modal')
# PWA install affordance in patient profile and home header.
app = replace_once(app, '      <div style={S.scr}>\n        {/* Equipo asistencial y código de vinculación */}', '      <div style={S.scr}>\n        {deferredInstallPrompt&&!pwaInstalled&&<button style={{...S.btnG,borderRadius:11,marginBottom:12,borderColor:D.green,color:D.green}} onClick={installNurseArt}>📲 Instalar NurseArt en este móvil</button>}\n        {/* Equipo asistencial y código de vinculación */}', 'PWA profile install button')
APP.write_text(app)

# PWA files and Firebase Hosting configuration --------------------------------
PUBLIC.mkdir(exist_ok=True)
(PUBLIC / 'manifest.webmanifest').write_text(dedent('''\
{
  "id": "/",
  "name": "NurseArt · Cuidados con tecnología",
  "short_name": "NurseArt",
  "description": "Portal de cuidados, farmacia y seguimiento clínico.",
  "lang": "es-ES",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#2563eb",
  "orientation": "portrait-primary",
  "icons": [
    {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
    {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ],
  "shortcuts": [
    {"name": "Mi medicación", "short_name": "Medicación", "url": "/?screen=pac-meds", "icons": [{"src": "/icons/icon-192.png", "sizes": "192x192"}]},
    {"name": "Farmacia", "short_name": "Farmacia", "url": "/?screen=pac-farmacia", "icons": [{"src": "/icons/icon-192.png", "sizes": "192x192"}]}
  ]
}
'''))
(PUBLIC / 'sw.js').write_text(dedent('''\
const CACHE_NAME = 'nurseart-shell-v1';
const APP_SHELL = ['/', '/index.html', '/manifest.webmanifest', '/offline.html', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const request = event.request;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then(response => { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put('/index.html', copy)); return response; }).catch(() => caches.match('/index.html').then(response => response || caches.match('/offline.html'))));
    return;
  }
  if (new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => { if (response.ok) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); } return response; })));
});
'''))
(PUBLIC / 'offline.html').write_text(dedent('''\
<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NurseArt sin conexión</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#eff6ff;color:#0f172a;font-family:system-ui,-apple-system,sans-serif}.card{max-width:330px;margin:24px;padding:28px;border-radius:24px;background:white;box-shadow:0 18px 48px #2563eb20;text-align:center}.mark{font-size:44px}h1{font-size:22px;margin:16px 0 8px}p{font-size:14px;line-height:1.55;color:#475569;margin:0}</style></head><body><main class="card"><div class="mark">🛡️</div><h1>Estás sin conexión</h1><p>NurseArt volverá a sincronizarse cuando recuperes internet. Puedes revisar el contenido que ya hayas abierto.</p></main></body></html>
'''))

# Create PWA 192px icon from the supplied 512px asset without overwriting it.
icon_512 = PUBLIC / 'icons' / 'icon-512.png'
icon_192 = PUBLIC / 'icons' / 'icon-192.png'
with Image.open(icon_512) as image:
    image.convert('RGBA').resize((192, 192), Image.Resampling.LANCZOS).save(icon_192)

index_html = (ROOT / 'index.html').read_text()
index_html = index_html.replace('<link rel="manifest" href="/manifest.json"/>', '<link rel="manifest" href="/manifest.webmanifest"/>')
index_html = index_html.replace('<meta name="theme-color" content="#2563EB"/>', '<meta name="theme-color" content="#2563EB"/>\n    <meta name="mobile-web-app-capable" content="yes"/>')
(ROOT / 'index.html').write_text(index_html)

main = (ROOT / 'src' / 'main.jsx').read_text()
main = replace_once(
    main,
    "ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)",
    "if ('serviceWorker' in navigator) { window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(error => console.warn('No se pudo registrar la PWA', error))); }\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)",
    'service worker registration',
)
(ROOT / 'src' / 'main.jsx').write_text(main)

(ROOT / 'firebase.json').write_text(dedent('''\
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{"source": "**", "destination": "/index.html"}]
  },
  "functions": {"source": "functions", "runtime": "nodejs20"},
  "firestore": {"rules": "firestore.rules"},
  "storage": {"rules": "storage.rules"}
}
'''))

# Project documentation and GitHub readiness.
(ROOT / '.gitignore').write_text(dedent('''\
node_modules/
dist/
.firebase/
.firebaserc.local
.env
.env.*
!.env.example
.DS_Store
npm-debug.log*
coverage/
'''))
(ROOT / 'README.md').write_text(dedent('''\
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
'''))
(ROOT / 'DEPLOYMENT.md').write_text(dedent('''\
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

El administrador debe disponer del claim personalizado `role: admin`. El repositorio conserva `scripts/assign-admin.cjs` como referencia de asignación. Ejecútalo únicamente desde un entorno con credenciales de Firebase Admin configuradas y con el UID revisado.

## PWA

La PWA usa `manifest.webmanifest` y `sw.js`. Para comprobar la instalación, usa HTTPS (Firebase Hosting lo proporciona) y abre la aplicación en Chrome para Android, Safari en iOS o Chrome de escritorio. En iOS, el usuario instala desde **Compartir → Añadir a pantalla de inicio**.
'''))
workflow = ROOT / '.github' / 'workflows'
workflow.mkdir(parents=True, exist_ok=True)
(workflow / 'ci.yml').write_text(dedent('''\
name: Validate NurseArt
on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run build
      - run: npm --prefix functions ci
      - run: npm --prefix functions run lint
'''))

print('Phase 4 implementation applied successfully.')
