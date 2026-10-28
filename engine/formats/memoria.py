"""Reto de memoria: memoriza una secuencia, desaparece, pregunta y revelación.

Campos del episodio:
  hook, sub         gancho
  sequence          lista de símbolos cortos (números o palabras) 5–8
  show_seconds      tiempo para memorizar
  question          pregunta tras ocultarla
  answer_index      posición (0-based) que se resalta en la revelación
  reveal, cta
"""
from render import Segment, W, H, font, ease_out


def _row(ctx, d, seq, y, size, hide=False, mark=None):
    f = font(ctx.f_bold, size)
    gap = 26
    widths = [max(f.getlength(s), size * 0.62) for s in seq]
    total = sum(widths) + gap * (len(seq) - 1)
    if total > W - 120:  # dos filas si no cabe
        half = (len(seq) + 1) // 2
        _row(ctx, d, seq[:half], y - size // 2 - 20, size, hide, mark if mark is not None and mark < half else None)
        _row(ctx, d, seq[half:], y + size // 2 + 20, size, hide,
             (mark - half) if mark is not None and mark >= half else None)
        return
    x = (W - total) / 2
    for i, (s, w) in enumerate(zip(seq, widths)):
        box = (x - 10, y - 10, x + w + 10, y + size + 20)
        if mark == i:
            d.rounded_rectangle(box, 24, fill=(*ctx.accent, 255))
            d.text((x + (w - f.getlength(s)) / 2, y), s, font=f, fill=(0, 0, 0))
        elif hide:
            d.rounded_rectangle(box, 24, fill=(255, 255, 255, 45))
            q = "?"
            d.text((x + (w - f.getlength(q)) / 2, y), q, font=f, fill=(255, 255, 255, 120))
        else:
            d.text((x + (w - f.getlength(s)) / 2, y), s, font=f, fill=ctx.fg, stroke_width=6, stroke_fill=(0, 0, 0))
        x += w + gap


def build(ctx, ep):
    seq = ep["sequence"]
    show = ep.get("show_seconds", 3.0)
    segs = []

    def memorize(ctx, img, d, t, p):
        ctx.text(d, ep["hook"], 230, 86, fname=ctx.f_bold, highlight=ep.get("hook_highlight"))
        ctx.text(d, ep["sub"], 560, 50, color=(220, 220, 220))
        _row(ctx, d, seq, 930, 150)
        ctx.bar(d, 1 - p, y=1320, color=ctx.bad if p > 0.66 else ctx.accent)
        left = max(0, show - t)
        ctx.text(d, f"{left:0.1f}s", 1380, 60, color=(220, 220, 220))

    segs.append(Segment(show, memorize,
                        [(0.0, "whoosh")] + [(float(i), "tick") for i in range(1, int(show) + 1)]))

    def ask(ctx, img, d, t, p):
        ctx.text(d, ep["question"], 300, 84, fname=ctx.f_bold, highlight=ep.get("question_highlight"))
        _row(ctx, d, seq, 930, 150, hide=True)
        n = 3 - int(t)
        f = font(ctx.f_bold, int(220 * (1 + 0.15 * (1 - ease_out((t % 1) * 3)))))
        s = str(max(1, n))
        d.text(((W - f.getlength(s)) / 2, 1250), s, font=f, fill=ctx.accent, stroke_width=8, stroke_fill=(0, 0, 0))

    segs.append(Segment(3.0, ask, [(0.0, "pop"), (1.0, "tick"), (2.0, "tick")]))

    def reveal(ctx, img, d, t, p):
        ctx.text(d, "Respuesta:", 300, 80, fname=ctx.f_bold)
        _row(ctx, d, seq, 760, 150, mark=ep["answer_index"])
        ctx.text(d, ep["reveal"], 1130, 52, color=(235, 235, 235))
        if t > 1.0:
            ctx.text(d, ep["cta"], 1460, 58, color=ctx.accent, fname=ctx.f_bold)

    segs.append(Segment(ep.get("reveal_seconds", 3.4), reveal, [(0.0, "ding")]))
    return segs
