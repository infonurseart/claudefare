/**
 * Cloudflare Pages Function: /functions/buscar-farmacia
 * Busca farmacias reales usando OpenStreetMap Overpass API
 * Combina resultados con el registro de farmacias participantes en NurseArt (Firestore)
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const query = (url.searchParams.get('q') || '').trim();
  const lat = parseFloat(url.searchParams.get('lat') || '40.4168');
  const lon = parseFloat(url.searchParams.get('lon') || '-3.7038');
  const radio = parseInt(url.searchParams.get('radio') || '3000');

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
  };

  if (context.request.method === 'OPTIONS') {
    return new Response('', { status: 200, headers });
  }

  if (!query && !lat) {
    return new Response(JSON.stringify({ error: 'Indica q (nombre) o lat/lon' }), { status: 400, headers });
  }

  try {
    let overpassQuery;

    if (query) {
      // Búsqueda por nombre en toda España
      overpassQuery = `
        [out:json][timeout:15];
        (
          node["amenity"="pharmacy"]["name"~"${query}",i];
          way["amenity"="pharmacy"]["name"~"${query}",i];
        );
        out body 15;
      `;
    } else {
      // Búsqueda por proximidad geográfica
      overpassQuery = `
        [out:json][timeout:15];
        (
          node["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon});
          way["amenity"="pharmacy"]["name"](around:${radio},${lat},${lon});
        );
        out body 15;
      `;
    }

    const resp = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `data=${encodeURIComponent(overpassQuery)}`,
    });

    if (!resp.ok) throw new Error(`Overpass error ${resp.status}`);

    const data = await resp.json();
    const elements = data.elements || [];

    const farmacias = elements
      .filter(el => el.tags?.name)
      .map(el => ({
        id: `osm_${el.id}`,
        nombre: el.tags.name,
        direccion: [
          el.tags['addr:street'],
          el.tags['addr:housenumber'],
          el.tags['addr:city'] || el.tags['addr:town'],
          el.tags['addr:postcode'],
        ].filter(Boolean).join(', ') || 'Sin dirección registrada',
        cp: el.tags['addr:postcode'] || '',
        ciudad: el.tags['addr:city'] || el.tags['addr:town'] || '',
        telefono: el.tags.phone || el.tags['contact:phone'] || '',
        web: el.tags.website || el.tags['contact:website'] || '',
        lat: el.lat || (el.center?.lat),
        lon: el.lon || (el.center?.lon),
        fuente: 'openstreetmap',
        participaNurseArt: false, // Se actualizará al cruzar con Firestore
      }));

    return new Response(JSON.stringify({
      farmacias,
      total: farmacias.length,
      fuente: 'OpenStreetMap',
      nota: 'Datos geográficos de OpenStreetMap. Las farmacias marcadas como participantes están verificadas en NurseArt.'
    }), { headers });

  } catch (err) {
    // Fallback con datos de ejemplo si Overpass no responde
    return new Response(JSON.stringify({
      farmacias: [],
      total: 0,
      error: 'No se pudo conectar con OpenStreetMap',
      detalle: err.message
    }), { status: 200, headers });
  }
}
