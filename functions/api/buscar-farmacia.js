// Cloudflare Pages Function — buscar-farmacia
// Llama a Overpass API server-side (sin restricciones CORS)
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const query = (url.searchParams.get('q') || '').trim();
  const lat   = parseFloat(url.searchParams.get('lat') || '40.4168');
  const lon   = parseFloat(url.searchParams.get('lon') || '-3.7038');
  const radio = parseInt(url.searchParams.get('radio') || '5000');

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=300', // cache 5 min
  };

  if (context.request.method === 'OPTIONS') {
    return new Response('', { status: 200, headers });
  }

  try {
    let oql;
    if (query) {
      // Búsqueda por nombre en toda España
      oql = `[out:json][timeout:25];area["ISO3166-1"="ES"][admin_level=2]->.c;(node["amenity"="pharmacy"]["name"~"${query}",i](area.c);way["amenity"="pharmacy"]["name"~"${query}",i](area.c););out body 25;`;
    } else {
      // Búsqueda por proximidad
      oql = `[out:json][timeout:25];(node["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon});way["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon}););out body 20;`;
    }

    // GET request — más simple y sin preflight
    const apiUrl = `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(oql)}`;
    const resp = await fetch(apiUrl, {
      headers: { 'User-Agent': 'NurseArt/1.0 (health app)' },
    });

    if (!resp.ok) throw new Error(`Overpass ${resp.status}`);
    const data = await resp.json();

    const farmacias = (data.elements || [])
      .filter(el => el.tags?.name)
      .map(el => ({
        id: `osm_${el.id}`,
        nombre: el.tags.name,
        direccion: [
          el.tags['addr:street'],
          el.tags['addr:housenumber'],
          el.tags['addr:city'] || el.tags['addr:town'] || el.tags['addr:municipality'],
          el.tags['addr:postcode'],
        ].filter(Boolean).join(', ') || 'Sin dirección registrada',
        cp:       el.tags['addr:postcode'] || '',
        ciudad:   el.tags['addr:city'] || el.tags['addr:town'] || el.tags['addr:municipality'] || '',
        telefono: el.tags.phone || el.tags['contact:phone'] || '',
        web:      el.tags.website || el.tags['contact:website'] || '',
        lat: el.lat ?? el.center?.lat,
        lon: el.lon ?? el.center?.lon,
        fuente: 'openstreetmap',
        participaNurseArt: false,
      }));

    return new Response(
      JSON.stringify({ farmacias, total: farmacias.length, fuente: 'OpenStreetMap' }),
      { headers }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ farmacias: [], total: 0, error: err.message }),
      { status: 200, headers }
    );
  }
}
