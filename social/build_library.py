"""Build ONE gallery of the whole media library so the owners can see everything in one place.

Scans assets/photos + assets/clips (the reel/story library that the save hooks + reels already use), makes a small
thumbnail for each item, writes them + a library.html into the website repo at /library, and pushes. Also lists which
items are currently used in the queue. Runs after any Telegram media is saved (save-photo / make-real) and daily.

Env: WEBSITE_TOKEN (push to website). ffmpeg for clip thumbnails.
  python social/build_library.py
"""
import json, os, subprocess, sys, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
PHOTOS = os.path.join(ROOT, "assets", "photos")
CLIPS = os.path.join(ROOT, "assets", "clips")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def load(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def run(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)


def main():
    plib = load(os.path.join(PHOTOS, "library.json"))
    clib = load(os.path.join(CLIPS, "library.json"))
    # what's currently used in the queue (so we can tag items IN USE / posted)
    q = load(os.path.join(BASE, "queue.json"))
    used = set()
    for sec in ("posts", "hold", "trials", "stories"):
        for it in q.get(sec, []):
            for k in ("video", "image", "cover"):
                if it.get(k):
                    used.add(os.path.basename(it[k]))

    url = f"https://x-access-token:{os.environ['WEBSITE_TOKEN']}@github.com/mdeshlahra123/vajraformwork.git"
    run("git", "clone", "-q", "--depth", "1", url, "site", check=True)
    out = os.path.join("site", "social", "library")
    os.makedirs(out, exist_ok=True)

    items = []
    # photos: thumbnail = the image itself, scaled down
    for f in sorted(os.listdir(PHOTOS)):
        if not f.endswith(".jpg"):
            continue
        key = f[:-4]
        meta = plib.get(key, {})
        thumb = f"ph-{f}"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(PHOTOS, f),
            "-vf", "scale=360:-1", "-q:v", "5", os.path.join(out, thumb))
        banned = (not meta.get("ok", True)) or any(b in f for b in ("sheet-held", "v1-hold", "v1-core", "dirty", "used"))
        items.append({"type": "photo", "name": f, "thumb": thumb, "desc": meta.get("desc", ""),
                      "ok": not banned, "added": meta.get("added", "")})
    # clips: thumbnail = a frame ~1s in
    for f in sorted(os.listdir(CLIPS)):
        if not f.endswith(".mp4") or f.endswith("-proxy.mp4"):
            continue
        meta = clib.get(f, {})
        thumb = f"cl-{f[:-4]}.jpg"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "1", "-i", os.path.join(CLIPS, f),
            "-frames:v", "1", "-vf", "scale=360:-1", "-q:v", "5", os.path.join(out, thumb))
        tag = "AI (Flow)" if meta.get("flow") else "real"
        items.append({"type": "clip", "name": f, "thumb": thumb, "desc": meta.get("note", "") or tag,
                      "ok": True, "added": meta.get("added", ""), "secs": meta.get("secs"), "flow": meta.get("flow", False)})

    photos = [i for i in items if i["type"] == "photo"]
    clips = [i for i in items if i["type"] == "clip"]

    def card(i):
        badge = "" if i["ok"] else '<span class="bad">BANNED</span>'
        sub = i["desc"][:90]
        extra = f" · {i['secs']}s" if i.get("secs") else ""
        tag = "AI" if i.get("flow") else ("photo" if i["type"] == "photo" else "clip")
        return (f'<figure>{badge}<img loading="lazy" src="{i["thumb"]}" alt="">'
                f'<figcaption><b>{i["name"]}</b><span>{tag}{extra}</span><small>{sub}</small></figcaption></figure>')

    html = f"""<!doctype html><html lang=en><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><meta name=robots content=noindex>
<title>VAJRA media library</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;background:#1e1a17;color:#efe9df;margin:0;padding:24px}}
h1{{font-size:26px;margin:0 0 4px}}.meta{{color:#cfc6b8;font-size:14px;margin-bottom:20px}}
h2{{border-top:1px solid #4a4038;padding-top:18px;margin-top:28px;font-size:19px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px}}
figure{{margin:0;background:#2a241f;border-radius:10px;overflow:hidden;position:relative}}
figure img{{width:100%;aspect-ratio:3/4;object-fit:cover;display:block}}
figcaption{{padding:8px 10px;font-size:12px;line-height:1.3}}
figcaption b{{display:block;word-break:break-all}}figcaption span{{color:#d9b46a;font-weight:700}}
figcaption small{{display:block;color:#cfc6b8;margin-top:3px}}
.bad{{position:absolute;top:6px;left:6px;background:#c0392b;color:#fff;font-size:10px;font-weight:700;padding:3px 7px;border-radius:4px;z-index:1}}
</style>
<h1>VAJRA media library</h1>
<div class=meta>Auto-updated {datetime.datetime.now(IST).strftime('%d %b %Y %H:%M IST')} · {len(photos)} photos · {len(clips)} clips · reels are built from the clips below · banned = not used in posts</div>
<h2>Clips ({len(clips)})</h2><div class=grid>{''.join(card(i) for i in clips)}</div>
<h2>Photos ({len(photos)})</h2><div class=grid>{''.join(card(i) for i in photos)}</div>
</html>"""
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)

    g = lambda *a: run("git", "-C", "site", *a)
    g("config", "user.name", "vajra-bot"); g("config", "user.email", "vajra-bot@users.noreply.github.com")
    g("add", "-A", "social/library")
    if run("git", "-C", "site", "diff", "--cached", "--quiet").returncode != 0:
        g("commit", "-q", "-m", f"library: {len(photos)} photos, {len(clips)} clips")
        g("push", "-q")
        print("pushed library:", len(photos), "photos,", len(clips), "clips")
    else:
        print("library unchanged")


if __name__ == "__main__":
    main()
