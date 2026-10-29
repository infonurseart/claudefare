export async function onRequest(context) {
  const url = new URL(context.request.url);
  const cn = url.searchParams.get('cn');
  const nombre = url.searchParams.get('nombre');
  const headers = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (context.request.method === 'OPTIONS') return new Response('', { status: 200, headers });
  try {
    let cimaUrl = cn
      ? `https://cima.aemps.es/cima/rest/medicamento?cn=${cn}`
      : `https://cima.aemps.es/cima/rest/medicamentos?nombre=${encodeURIComponent(nombre)}&estado=1`;
    const resp = await fetch(cimaUrl, { headers: { 'Accept': 'application/json' } });
    if (!resp.ok) throw new Error(`CIMA ${resp.status}`);
    const data = await resp.json();
    return new Response(JSON.stringify(data), { headers });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 200, headers });
  }
}
