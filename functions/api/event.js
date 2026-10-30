// POST /api/event → contador anónimo de uso (sin cookies ni datos personales)
const ALLOWED = new Set(['calc_comprar', 'calc_vender', 'calc_hipoteca', 'calc_reforma', 'lead_reforma', 'lead_venta', 'lead_hipoteca']);

export async function onRequestPost({ request, env }) {
  try {
    const { e } = await request.json();
    if (ALLOWED.has(e) && env.STATS) {
      const day = new Date().toISOString().slice(0, 10);
      const key = `${day}:${e}`;
      const n = parseInt((await env.STATS.get(key)) || '0', 10) + 1;
      await env.STATS.put(key, String(n), { expirationTtl: 60 * 60 * 24 * 400 });
    }
  } catch {}
  return new Response(null, { status: 204 });
}
