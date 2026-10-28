"""Motor de render multi-marca.

Uso:  python3 engine/render.py engine/episodes/<archivo>.json salida.mp4

Un episodio (JSON) indica la marca, el formato y el contenido. El formato
construye una lista de segmentos (duración + función de dibujo + sonidos).
Todo se genera por código: sin clips de stock, sin servicios de pago.
"""
import importlib
import json
import math
import os
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SR = 44100
ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- utilidades
def hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=64)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(ROOT, "fonts", name), size)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


@dataclass
class Segment:
    duration: float
    draw: Callable  # draw(ctx, img, d, t, p) ; t=segundos locales, p=progreso 0..1
    sounds: List[Tuple[float, str]] = field(default_factory=list)  # (t local, tipo)


class Ctx:
    """Estilo de marca + primitivas de dibujo comunes a todos los formatos."""

    def __init__(self, brand: dict):
        self.brand = brand
        s = brand["style"]
        self.fg = hex_rgb(s["text"])
        self.accent = hex_rgb(s["accent"])
        self.good = hex_rgb(s["good"])
        self.bad = hex_rgb(s["bad"])
        self.f_bold, self.f_body, self.f_small = s["font_bold"], s["font_body"], s["font_small"]
        self._bg = self._gradient(hex_rgb(s["background"][0]), hex_rgb(s["background"][1]))

    @staticmethod
    def _gradient(c1, c2) -> Image.Image:
        y = np.linspace(0, 1, H)[:, None, None]
        arr = (np.array(c1) * (1 - y) + np.array(c2) * y).astype(np.uint8)
        return Image.fromarray(np.repeat(arr, W, axis=1), "RGB")

    def background(self) -> Image.Image:
        return self._bg.copy()

    def wrap(self, text: str, f, max_w: int) -> List[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if f.getlength(test) <= max_w or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def text(self, d: ImageDraw.ImageDraw, txt: str, y: int, size: int, color=None,
             fname=None, max_w=920, stroke=6, highlight=None, line_gap=1.12, anchor_mid=False):
        """Texto centrado y envuelto. `highlight`: palabras pintadas en el color de acento."""
        f = font(fname or self.f_body, size)
        lines = self.wrap(txt, f, max_w)
        lh = int(size * line_gap)
        if anchor_mid:
            y = y - (lh * len(lines)) // 2
        hl = {h.lower().strip("¿?¡!.,") for h in (highlight or [])}
        for i, line in enumerate(lines):
            ly = y + i * lh
            x = (W - f.getlength(line)) / 2
            for word in line.split(" "):
                col = self.accent if word.lower().strip("¿?¡!.,") in hl else (color or self.fg)
                d.text((x, ly), word, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))
                x += f.getlength(word + " ")
        return y + lh * len(lines)

    def handle(self, d):
        f = font(self.f_small, 34)
        h = self.brand["handle"]
        d.text(((W - f.getlength(h)) / 2, H - 150), h, font=f, fill=(255, 255, 255, 150))

    def bar(self, d, p: float, y=150, color=None):
        d.rounded_rectangle((90, y, W - 90, y + 18), 9, fill=(255, 255, 255, 40))
        d.rounded_rectangle((90, y, 90 + max(18, int((W - 180) * p)), y + 18), 9, fill=color or self.accent)


# --------------------------------------------------------------------- audio
def _tone(freq, dur, vol=0.35, decay=18.0):
    t = np.arange(int(SR * dur)) / SR
    return vol * np.sin(2 * math.pi * freq * t) * np.exp(-decay * t)


SOUNDS = {
    "tick": lambda: _tone(1500, 0.06, 0.25, 60),
    "pop": lambda: _tone(660, 0.12, 0.35, 30),
    "ding": lambda: np.concatenate([_tone(880, 0.12, 0.4, 10), _tone(1320, 0.45, 0.4, 7)]),
    "buzz": lambda: _tone(140, 0.35, 0.35, 6) * np.sign(np.sin(np.arange(int(SR * 0.35)) / SR * 2 * math.pi * 70)),
    "whoosh": lambda: (np.random.default_rng(1).standard_normal(int(SR * 0.3))
                       * np.hanning(int(SR * 0.3)) * 0.12),
}


def build_audio(segments: List[Segment], path: str) -> float:
    total = sum(s.duration for s in segments)
    buf = np.zeros(int(SR * total) + SR)
    start = 0.0
    for s in segments:
        for (tl, kind) in s.sounds:
            snd = SOUNDS[kind]()
            i = int((start + tl) * SR)
            buf[i:i + len(snd)] += snd[: len(buf) - i]
        start += s.duration
    buf = buf[: int(SR * total)]
    pcm = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return total


# -------------------------------------------------------------------- render
def render(episode_path: str, out_path: str) -> dict:
    ep = json.load(open(episode_path, encoding="utf-8"))
    brand = json.load(open(os.path.join(ROOT, "brands", ep["brand"] + ".json"), encoding="utf-8"))
    ctx = Ctx(brand)
    fmt = importlib.import_module(f"formats.{ep['format']}")
    segments: List[Segment] = fmt.build(ctx, ep)

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        total = build_audio(segments, wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for seg in segments:
            n = max(1, round(seg.duration * FPS))
            for i in range(n):
                img = ctx.background()
                d = ImageDraw.Draw(img, "RGBA")
                t = i / FPS
                seg.draw(ctx, img, d, t, i / max(1, n - 1))
                ctx.handle(d)
                proc.stdin.write(img.tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg falló")
    return {"duration": round(total, 2), "segments": len(segments)}


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    print(json.dumps(render(sys.argv[1], sys.argv[2]), ensure_ascii=False))
