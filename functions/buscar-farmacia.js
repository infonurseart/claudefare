export async function onRequest(context) {
  const url = new URL(context.request.url);
  const query = (url.searchParams.get('q') || '').trim();
  const lat = parseFloat(url.searchParams.get('lat') || '40.4168');
  const lon = parseFloat(url.searchParams.get('lon') || '-3.7038');
  const radio = parseInt(url.searchParams.get('radio') || '3000');
  const headers = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (context.request.method === 'OPTIONS') return new Response('', { status: 200, headers });
  try {
    let overpassQuery = query
      ? `[out:json][timeout:15];(node["amenity"="pharmacy"]["name"~"${query}",i];way["amenity"="pharmacy"]["name"~"${query}",i];);out body 15;`
      : `[out:json][timeout:15];(node["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon});way["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon}););out body 15;`;
    const resp = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `data=${encodeURIComponent(overpassQuery)}`,
    });
    if (!resp.ok) throw new Error(`Overpass ${resp.status}`);
    const data = await resp.json();
    const farmacias = (data.elements || []).filter(el => el.tags?.name).map(el => ({
      id: `osm_${el.id}`,
      nombre: el.tags.name,
      direccion: [el.tags['addr:street'], el.tags['addr:housenumber'], el.tags['addr:city'] || el.tags['addr:town'], el.tags['addr:postcode']].filter(Boolean).join(', ') || 'Sin dirección registrada',
      cp: el.tags['addr:postcode'] || '',
      ciudad: el.tags['addr:city'] || el.tags['addr:town'] || '',
      telefono: el.tags.phone || el.tags['contact:phone'] || '',
      web: el.tags.website || el.tags['contact:website'] || '',
      lat: el.lat || el.center?.lat,
      lon: el.lon || el.center?.lon,
      fuente: 'openstreetmap',
      participaNurseArt: false,
    }));
    return new Response(JSON.stringify({ farmacias, total: farmacias.length, fuente: 'OpenStreetMap' }), { headers });
  } catch (err) {
    return new Response(JSON.stringify({ farmacias: [], total: 0, error: err.message }), { status: 200, headers });
  }
}
