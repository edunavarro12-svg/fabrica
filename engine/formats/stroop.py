"""Reto Stroop: el espectador debe decir el COLOR de la tinta, no la palabra.

Campos del episodio:
  hook, sub         textos del gancho (fotograma 0)
  items             [[palabra, color_hex], ...]  (5–8)
  item_seconds      tiempo por palabra (acelera si se da lista)
  reveal            explicación breve al final
  cta               llamada a comentar
"""
from render import Segment, W, H, font, ease_out, hex_rgb


def build(ctx, ep):
    segs = []
    items = ep["items"]
    per = ep.get("item_seconds", 1.1)
    per_list = per if isinstance(per, list) else [per] * len(items)
    total_items = len(items)

    # 1) Gancho: visible desde el primer fotograma, con la primera palabra ya en pantalla.
    first_w, first_c = items[0]

    def hook(ctx, img, d, t, p):
        ctx.text(d, ep["hook"], 260, 92, fname=ctx.f_bold, highlight=ep.get("hook_highlight"))
        ctx.text(d, ep["sub"], 640, 52, color=(220, 220, 220))
        s = 1 + 0.04 * (1 - ease_out(p))
        base = 190
        while font(ctx.f_bold, base).getlength(first_w) > W - 160:
            base -= 6
        f = font(ctx.f_bold, int(base * s))
        tw = f.getlength(first_w)
        d.text(((W - tw) / 2, 1020), first_w, font=f, fill=hex_rgb(first_c), stroke_width=8, stroke_fill=(0, 0, 0))
        ctx.text(d, "¡EMPIEZA!", 1400, 64, color=ctx.accent, fname=ctx.f_bold)

    segs.append(Segment(2.2, hook, [(0.0, "whoosh"), (1.3, "pop")]))

    # 2) Palabras, cada vez más rápido.
    for idx, ((word, color), dur) in enumerate(zip(items, per_list)):
        def draw(ctx, img, d, t, p, word=word, color=color, idx=idx):
            ctx.bar(d, (idx + p) / total_items)
            ctx.text(d, "Di el COLOR", 230, 70, fname=ctx.f_bold, highlight=["COLOR"])
            s = 1 + 0.12 * (1 - ease_out(min(1, t * 6)))
            base = 210
            while font(ctx.f_bold, base).getlength(word) > W - 160:
                base -= 6
            f = font(ctx.f_bold, int(base * s))
            tw = f.getlength(word)
            d.text(((W - tw) / 2, H / 2 - 140), word, font=f, fill=hex_rgb(color),
                   stroke_width=8, stroke_fill=(0, 0, 0))
            ctx.text(d, f"{idx + 1}/{total_items}", 1380, 56, color=(200, 200, 200))
        segs.append(Segment(dur, draw, [(0.0, "tick")]))

    # 3) Revelación y llamada a comentar.
    def reveal(ctx, img, d, t, p):
        ctx.text(d, "¿Cuántas fallaste?", 330, 96, fname=ctx.f_bold, highlight=["fallaste?"])
        ctx.text(d, ep["reveal"], 720, 56, color=(235, 235, 235))
        if t > 1.0:
            ctx.text(d, ep["cta"], 1330, 60, color=ctx.accent, fname=ctx.f_bold)

    segs.append(Segment(ep.get("reveal_seconds", 3.2), reveal, [(0.0, "ding")]))
    return segs
