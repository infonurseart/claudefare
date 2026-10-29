// Cloudflare Pages Function — /api/buscar-farmacia
// Busca farmacias en OpenStreetMap con múltiples mirrors de fallback
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const query = (url.searchParams.get('q') || '').trim();
  const lat   = parseFloat(url.searchParams.get('lat') || '40.4168');
  const lon   = parseFloat(url.searchParams.get('lon') || '-3.7038');
  const radio = parseInt(url.searchParams.get('radio') || '5000');

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=300',
  };

  if (context.request.method === 'OPTIONS') {
    return new Response('', { status: 200, headers });
  }

  // Query simple sin filtro de país — más rápida y compatible con todos los mirrors
  const oql = query
    ? `[out:json][timeout:20];(node["amenity"="pharmacy"]["name"~"${query}",i];way["amenity"="pharmacy"]["name"~"${query}",i];);out body 30;`
    : `[out:json][timeout:20];(node["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon});way["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon}););out body 20;`;

  const encoded = encodeURIComponent(oql);

  // Mirrors en orden — el Worker los prueba todos hasta que uno responde
  const mirrors = [
    `https://overpass-api.de/api/interpreter?data=${encoded}`,
    `https://overpass.kumi.systems/api/interpreter?data=${encoded}`,
    `https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=${encoded}`,
    `https://overpass.openstreetmap.ru/api/interpreter?data=${encoded}`,
  ];

  const parsear = (data) => (data.elements || [])
    .filter(el => el.tags?.name)
    .map(el => ({
      id:       `osm_${el.id}`,
      nombre:   el.tags.name,
      direccion:[el.tags['addr:street'], el.tags['addr:housenumber'],
                 el.tags['addr:city'] || el.tags['addr:town'],
                 el.tags['addr:postcode']].filter(Boolean).join(', ') || 'Sin dirección registrada',
      cp:       el.tags['addr:postcode'] || '',
      ciudad:   el.tags['addr:city'] || el.tags['addr:town'] || el.tags['addr:municipality'] || '',
      telefono: el.tags.phone || el.tags['contact:phone'] || '',
      web:      el.tags.website || el.tags['contact:website'] || '',
      lat:      el.lat ?? el.center?.lat,
      lon:      el.lon ?? el.center?.lon,
      fuente:   'openstreetmap',
      participaNurseArt: false,
    }));

  for (const mirrorUrl of mirrors) {
    try {
      const resp = await fetch(mirrorUrl, {
        headers: { 'User-Agent': 'NurseArt/1.0 (health app; contact@nurseart.es)' },
        signal: AbortSignal.timeout(18000),
      });
      if (!resp.ok) continue;
      const data = await resp.json();
      const farmacias = parsear(data);
      return new Response(
        JSON.stringify({ farmacias, total: farmacias.length, fuente: 'OpenStreetMap' }),
        { headers }
      );
    } catch (_) { continue; }
  }

  return new Response(
    JSON.stringify({ farmacias: [], total: 0, error: 'Todos los servidores de búsqueda no disponibles. Inténtalo en unos minutos.' }),
    { status: 200, headers }
  );
}
