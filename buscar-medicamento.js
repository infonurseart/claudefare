// Cloudflare Pages Function (diferente a Netlify Function)
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const query = (url.searchParams.get('q')||'').trim();
  const cn = (url.searchParams.get('cn')||'').trim();

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
  };

  if(context.request.method === 'OPTIONS'){
    return new Response('', {status:200, headers});
  }

  if(!query && !cn){
    return new Response(JSON.stringify({error:'Indica q o cn'}), {status:400, headers});
  }

  const CIMA = 'https://cima.aemps.es/cima/rest';

  try {
    if(cn){
      const cnsToTry = [...new Set([cn, cn.replace(/^0+/,''), cn.padStart(6,'0')])];
      for(const cnV of cnsToTry){
        const res = await fetch(`${CIMA}/medicamento?cn=${encodeURIComponent(cnV)}`, {
          headers:{'User-Agent':'NurseArt/1.0','Accept':'application/json'}
        });
        if(res.status === 200){
          const m = await res.json();
          if(m.nombre){
            return new Response(JSON.stringify({
              medicamentos:[normalizar(m)], total:1, source:'cima', cn:cnV
            }), {headers});
          }
        }
      }
      return new Response(JSON.stringify({medicamentos:[], total:0}), {headers});
    }

    if(query.length < 2){
      return new Response(JSON.stringify({error:'Mínimo 2 caracteres'}), {status:400, headers});
    }

    const res = await fetch(
      `${CIMA}/medicamentos?nombre=${encodeURIComponent(query)}&pagina=1&itemsPerPagina=10`,
      {headers:{'User-Agent':'NurseArt/1.0','Accept':'application/json'}}
    );
    if(!res.ok) throw new Error('CIMA '+res.status);
    const data = await res.json();
    return new Response(JSON.stringify({
      medicamentos:(data.resultados||[]).map(normalizar),
      total:data.totalFilas||0, source:'cima'
    }), {headers});

  } catch(err){
    return new Response(JSON.stringify({error:'Error CIMA', detail:err.message}), {status:500, headers});
  }
}

function normalizar(m){
  const principioActivo=(m.principiosActivos||[]).map(p=>p.nombre).join(' + ')||'No especificado';
  let fotoUrl=null;
  if(Array.isArray(m.fotos)&&m.fotos.length>0){
    const f=m.fotos.find(f=>f.tipo==='materialas')||m.fotos[0];
    fotoUrl=f?.url||null;
  }
  const cn=(m.presentaciones?.[0]?.cn)||m.cn||null;
  return{
    nombre:m.nombre||'Desconocido', principioActivo,
    lab:m.labtitular||'No especificado',
    presentacion:m.formaFarmaceutica?.nombre||'',
    nregistro:m.nregistro||null, cn,
    efg:!!m.generico, receta:!!m.receta,
    comercializado:m.comerc!==false, fotoUrl
  };
}
