// POST /api/leads → valida el formulario y lo envía a Make (hoja de Google + email)
const SERVICES = { reforma: 'Reforma', venta: 'Vender', hipoteca: 'Hipoteca' };

const clean = (v, max) =>
  String(v ?? '')
    .replace(/[\u0000-\u001f<>]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, max);

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
  });

const madridNow = () =>
  new Intl.DateTimeFormat('es-ES', { timeZone: 'Europe/Madrid', dateStyle: 'short', timeStyle: 'short' }).format(new Date());

export async function onRequestPost({ request, env }) {
  let b;
  try {
    b = await request.json();
  } catch {
    return json({ error: 'Solicitud no válida.' }, 400);
  }
  // Campo trampa para bots: si viene relleno, respondemos OK sin hacer nada.
  if (clean(b.website, 200)) return json({ ok: true });

  const service = clean(b.service, 20);
  if (!SERVICES[service]) return json({ error: 'Servicio no válido.' }, 400);
  const nombre = clean(b.name, 80);
  const telefono = clean(b.phone, 30);
  const email = clean(b.email, 120).toLowerCase();
  const zona = clean(b.zone, 120);
  const cuando = clean(b.when, 60);
  const detalle = clean(b.detail, 1500);
  const digits = telefono.replace(/\D/g, '');
  const phoneOk = digits.length >= 9 && digits.length <= 15;
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
  if (!phoneOk && !emailOk) return json({ error: 'Déjanos un email o un teléfono.' }, 400);
  if (telefono && !phoneOk) return json({ error: 'Revisa el teléfono.' }, 400);
  if (email && !emailOk) return json({ error: 'Revisa el email.' }, 400);
  if (b.consent !== true) return json({ error: 'Necesitamos tu consentimiento para pasar tus datos.' }, 400);

  const webhook = env.LEADS_WEBHOOK;
  if (!webhook) return json({ error: 'Servicio no configurado.' }, 503);

  const fecha = madridNow();
  const payload = {
    id: crypto.randomUUID(),
    fecha,
    servicio: SERVICES[service],
    nombre,
    telefono,
    email,
    zona,
    cuando,
    detalle,
    consentimiento: `Sí · ${fecha} · texto v1`,
    origen: new URL(request.url).hostname,
  };

  const r = await fetch(webhook, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    console.error('lead_forward_error', r.status);
    return json({ error: 'No hemos podido guardar tu solicitud. Inténtalo de nuevo.' }, 502);
  }
  return json({ ok: true });
}
