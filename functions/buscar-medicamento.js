export async function onRequest(context) {
  const url = new URL(context.request.url);
  const q = (url.searchParams.get('q')||'').trim();
  const cn = (url.searchParams.get('cn')||'').trim();
  const headers = {'Access-Control-Allow-Origin':'*','Content-Type':'application/json'};
  if(context.request.method==='OPTIONS') return new Response('',{status:200,headers});
  const CIMA='https://cima.aemps.es/cima/rest';
  function normalizar(m){
    const principioActivo=(m.principiosActivos||[]).map(p=>p.nombre).join(' + ')||'No especificado';
    let fotoUrl=null;
    if(Array.isArray(m.fotos)&&m.fotos.length>0){const f=m.fotos.find(f=>f.tipo==='materialas')||m.fotos[0];fotoUrl=f?.url||null;}
    return{nombre:m.nombre||'Desconocido',principioActivo,lab:m.labtitular||'',presentacion:m.formaFarmaceutica?.nombre||'',nregistro:m.nregistro||null,cn:(m.presentaciones?.[0]?.cn)||m.cn||null,efg:!!m.generico,receta:!!m.receta,comercializado:m.comerc!==false,fotoUrl};
  }
  try{
    if(cn){
      const variants=[...new Set([cn,cn.replace(/^0+/,''),cn.padStart(6,'0')])];
      for(const v of variants){
        const res=await fetch(`${CIMA}/medicamento?cn=${encodeURIComponent(v)}`,{headers:{'User-Agent':'NurseArt/1.0','Accept':'application/json'}});
        if(res.status===200){const m=await res.json();if(m.nombre)return new Response(JSON.stringify({medicamentos:[normalizar(m)],total:1,source:'cima',cn:v}),{headers});}
      }
      return new Response(JSON.stringify({medicamentos:[],total:0}),{headers});
    }
    if(q.length<2) return new Response(JSON.stringify({error:'Mínimo 2 caracteres'}),{status:400,headers});
    const res=await fetch(`${CIMA}/medicamentos?nombre=${encodeURIComponent(q)}&pagina=1&itemsPerPagina=10`,{headers:{'User-Agent':'NurseArt/1.0','Accept':'application/json'}});
    if(!res.ok) throw new Error('CIMA '+res.status);
    const data=await res.json();
    return new Response(JSON.stringify({medicamentos:(data.resultados||[]).map(normalizar),total:data.totalFilas||0,source:'cima'}),{headers});
  }catch(err){return new Response(JSON.stringify({error:'Error CIMA',detail:err.message}),{status:500,headers});}
}
