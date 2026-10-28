"""Publica un MP4 como Reel en Instagram (API con inicio de sesión de Instagram).

Uso:  python3 engine/publish_instagram.py <episodio.json> <video.mp4>

- La API de Instagram exige una URL pública del vídeo: el flujo de GitHub Actions
  despliega el MP4 en GitHub Pages con un nombre imposible de adivinar
  (PUBLIC_VIDEO_URL) y lo retira en cuanto termina.
- Idempotente: si el episodio ya figura en engine/ledger/<brand>.json para Instagram,
  no vuelve a publicar.
- Nunca imprime el token.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://graph.instagram.com/v21.0"
ROOT = os.path.dirname(os.path.abspath(__file__))


def _req(method, url, token, data=None, headers=None, body=None, timeout=120):
    h = {"Authorization": f"Bearer {token}"}
    h.update(headers or {})
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:500]
        raise RuntimeError(f"HTTP {e.code} en {url.split('?')[0]}: {msg}") from None


def ledger_path(brand):
    return os.path.join(ROOT, "ledger", f"{brand}.json")


def load_ledger(brand):
    p = ledger_path(brand)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"published": []}


def save_ledger(brand, ledger):
    os.makedirs(os.path.dirname(ledger_path(brand)), exist_ok=True)
    json.dump(ledger, open(ledger_path(brand), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    ep_path, video = sys.argv[1:3]
    ep = json.load(open(ep_path, encoding="utf-8"))
    brand_id, caption = ep["brand"], ep["caption"]
    episode_id = os.path.basename(ep_path)[:-5]
    brand = json.load(open(os.path.join(ROOT, "brands", f"{brand_id}.json"), encoding="utf-8"))
    token = os.environ["IG_TOKEN"]
    user = brand["instagram_user_id"]

    ledger = load_ledger(brand_id)
    if any(p["episode"] == episode_id and p["platform"] == "instagram" for p in ledger["published"]):
        print(f"::notice title=Skip::{episode_id} ya publicado en Instagram; no se repite")
        return

    public_url = os.environ["PUBLIC_VIDEO_URL"]
    c = _req("POST", f"{API}/{user}/media", token,
             data={"media_type": "REELS", "video_url": public_url, "caption": caption,
                   "share_to_feed": "true"})
    cid = c["id"]
    # Se anota el intento antes de subir: si algo falla después, se revisa a mano en vez de duplicar.
    ledger.setdefault("attempts", []).append({"episode": episode_id, "platform": "instagram",
                                              "container": cid, "at": int(time.time())})
    save_ledger(brand_id, ledger)

    for _ in range(60):
        st = _req("GET", f"{API}/{cid}?fields=status_code,status", token)
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Procesado fallido: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram no terminó de procesar el vídeo a tiempo")

    pub = _req("POST", f"{API}/{user}/media_publish", token, data={"creation_id": cid})
    media_id = pub["id"]
    info = _req("GET", f"{API}/{media_id}?fields=permalink,timestamp", token)
    ledger["published"].append({"episode": episode_id, "platform": "instagram", "media_id": media_id,
                                "permalink": info.get("permalink"), "at": info.get("timestamp")})
    save_ledger(brand_id, ledger)
    print(f"::notice title=Publicado::{info.get('permalink')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # error visible como anotación, sin tokens
        print(f"::error title=Instagram::{str(exc)[:600]}")
        sys.exit(1)
