# HogarZGZ

Calculadoras de vivienda en Zaragoza · https://hogarzgz.es

- Web estática (`index.html`, `styles.css`, `app.js`) servida por Cloudflare Pages.
- `functions/api/leads.js`: recibe los formularios de leads y los reenvía al escenario de Make
  (hoja "Leads HogarZGZ" + email). La URL del webhook va en la variable de entorno `LEADS_WEBHOOK`.
- `functions/api/event.js`: contador anónimo de uso (KV opcional `STATS`).

Cada cambio subido a la rama `main` se publica solo en Cloudflare.
