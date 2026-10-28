"""Reto visual: encuentra el elemento distinto antes de que acabe la cuenta atrás.

Campos del episodio:
  hook, sub
  base, odd         carácter repetido y carácter intruso (p. ej. "6" y "9")
  cols, rows        tamaño de la cuadrícula
  odd_pos           [col, fila] del intruso (si falta, se elige con `seed`)
  seconds           duración de la búsqueda
  reveal, cta
"""
import random

from render import Segment, W, H, font


def build(ctx, ep):
    cols, rows = ep.get("cols", 9), ep.get("rows", 12)
    rnd = random.Random(ep.get("seed", 7))
    oc, orow = ep.get("odd_pos") or (rnd.randrange(1, cols - 1), rnd.randrange(1, rows - 1))
    secs = ep.get("seconds", 5)
    cell = min((W - 120) // cols, 900 // rows)
    size = int(cell * 0.82)
    gx = (W - cell * cols) / 2
    gy = 500

    def grid(d, mark=False):
        f = font(ctx.f_bold, size)
        for r in range(rows):
            for c in range(cols):
                ch = ep["odd"] if (c, r) == (oc, orow) else ep["base"]
                x = gx + c * cell + (cell - f.getlength(ch)) / 2
                y = gy + r * cell
                d.text((x, y), ch, font=f, fill=ctx.fg)
        if mark:
            cx, cy = gx + oc * cell + cell / 2, gy + orow * cell + cell / 2
            rad = cell * 0.85
            d.ellipse((cx - rad, cy - rad + size * 0.1, cx + rad, cy + rad + size * 0.1),
                      outline=ctx.bad, width=12)

    segs = []

    def search(ctx, img, d, t, p):
        ctx.text(d, ep["hook"], 200, 78, fname=ctx.f_bold, highlight=ep.get("hook_highlight"))
        ctx.text(d, ep["sub"], 400, 46, color=(220, 220, 220))
        grid(d)
        ctx.bar(d, 1 - p, y=gy + rows * cell + 50, color=ctx.bad if p > 0.7 else ctx.accent)
        n = max(1, secs - int(t))
        ctx.text(d, str(n), gy + rows * cell + 100, 110, color=ctx.accent, fname=ctx.f_bold)

    segs.append(Segment(secs, search, [(0.0, "whoosh")] + [(float(i), "tick") for i in range(1, secs)]))

    def reveal(ctx, img, d, t, p):
        ctx.text(d, "¡Aquí estaba!", 200, 86, fname=ctx.f_bold, highlight=["Aquí"])
        grid(d, mark=(int(t * 4) % 2 == 0) or t > 0.8)
        ctx.text(d, ep["reveal"], gy + rows * cell + 50, 48, color=(235, 235, 235))
        if t > 1.0:
            ctx.text(d, ep["cta"], gy + rows * cell + 210, 56, color=ctx.accent, fname=ctx.f_bold)

    segs.append(Segment(ep.get("reveal_seconds", 3.2), reveal, [(0.0, "ding")]))
    return segs
