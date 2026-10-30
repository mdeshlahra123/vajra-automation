"""Daily unique Instagram Story (not a copy of the post). Runs in post.yml after each post (morning + evening).
Each run: picks a story TYPE (rotates), a real photo not used recently, and a fresh Hinglish line
(Gemini free key writes it, claims guard checks it; falls back to a line bank), renders a 1080x1920 card,
uploads it to the website repo, publishes it as a Story, and remembers what was used (social/story-state.json).
API stories can't have stickers, so every story ends with a reply ask ("Reply karo PP") -> replies land in DMs.
  python social/story.py            make + post one story
  python social/story.py --dry      make the image only (work/story.jpg), don't post
Env: META_TOKEN, WEBSITE_TOKEN, GEMINI_FREE_KEY/GEMINI_API_KEY (optional), TELEGRAM_* (optional, to show owners).
"""
import datetime, json, os, random, re, subprocess, sys, time, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(BASE, "engine"))
STATE = os.path.join(BASE, "story-state.json")
IG, V = "17841424780649708", "https://graph.facebook.com/v24.0"
FONT = os.path.join(ROOT, "assets", "brand", "Archivo.ttf")
LOGO = os.path.join(ROOT, "assets", "brand", "logo.png")
# real photos allowed in stories (never the dirty sheet or ply pile as a VAJRA shot)
PHOTOS = ["slab-underside", "beam-box", "sheet-cut", "column-smooth2", "finish-column", "godown", "warehouse", "sheet-thin", "v5-cage", "v6-close", "v6-done", "p2-column", "r-workers", "v4-point"]
TYPES = {
    "sawal": "a simple question to contractors that makes them reply (e.g. 'Aapki site pe kitni ply har mahine kharab hoti hai?')",
    "myth": "'Log kehte hain ... / Sach ...' myth vs fact about PP shuttering vs ply (only allowed claims)",
    "tip": "one practical site tip about shuttering/dhalai/handling that helps a contractor today",
    "site": "a short 'aaj site pe' style line describing the real photo shown (column/slab/beam/godown/stock)",
    "ya": "a this-or-that question: 'Ply ya PP? Reply karo' style, playful",
    "offer": "the free sample offer: 1x1 ft sample piece, sirf delivery charge, reply karo SAMPLE",
}
BANK = {
    "sawal": ["Aapki site pe har mahine kitni ply kharab hoti hai?", "Shuttering mein sabse bada sar-dard kya hai?", "Aap abhi ply use karte ho ya PP?"],
    "myth": ["Log kehte hain: plastic sheet kamzor hoti hai. Sach: VAJRA sheet site ki maar jhel leti hai.",
             "Log kehte hain: PP mehnga padta hai. Sach: ply se 2-3 guna zyada chalti hai, sahi handling ke saath."],
    "tip": ["Dhalai ke turant baad sheet paani se dho lo, agli baar finish aur saaf aayegi.", "Sheet ko seedha zameen pe na ghaseeto, utha ke rakho: zyada chalegi."],
    "site": ["Aaj site pe: column VAJRA sheet se, finish ekdum smooth.", "Ready stock, aaj hi dispatch."],
    "ya": ["Ply ya PP? Reply karo.", "Bhaari ply ya halki PP sheet? Aap batao."],
    "offer": ["Free sample chahiye? 1x1 ft piece, sirf delivery charge. Reply karo SAMPLE."],
}
ASK = {"sawal": "Reply karke batao", "myth": "Rate chahiye? Reply karo PP", "tip": "Aisi tips ke liye follow karo",
       "site": "Rate ke liye reply karo PP", "ya": "Reply karo: PLY ya PP", "offer": "Reply karo SAMPLE"}


def load():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"n": 0, "photos": [], "lines": []}


def write_line(kind, photo, used):
    try:
        import gem, claims
        rules = open(os.path.join(BASE, "engine", "brand.md"), encoding="utf-8").read()
        q = (f"Brand rules:\n{rules}\n\nWrite ONE Instagram Story line in Hinglish (Roman script) for VAJRA PP shuttering sheet, type: {TYPES[kind]}. "
             f"The background photo shows: {photo.replace('-', ' ')}. Max 14 words, sentence case, no hashtags, no emoji, no price, no number of uses, "
             f"no invented numbers. Must be different from these recent lines: {used[-15:]}. Return JSON only: {{\"line\": \"...\"}}")
        line = claims.fix_line(gem.text("gemini-3.5-flash-lite", q, json_mode=True)["line"].strip(), short=False)
        if 3 <= len(line.split()) <= 18 and not re.search(r"\d{2,}|₹|rs\.?\s?\d", line, re.I) and line not in used:
            return line
    except Exception as e:
        print("AI line failed, using bank:", str(e)[:120])
    left = [l for l in BANK[kind] if l not in used] or BANK[kind]
    return random.choice(left)


def wrap(text, n=20):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur] if cur else lines


def render(photo, line, ask, out):
    work = os.path.dirname(out); os.makedirs(work, exist_ok=True)
    esc = lambda p: p.replace("\\", "/").replace(":", "\\:")
    rows = wrap(line, 20)[:6]
    files = []
    for i, r in enumerate(rows + [ask]):
        f = os.path.join(work, f"st{i}.txt"); open(f, "w", encoding="utf-8").write(r); files.append(esc(f))
    y0 = 1180 - len(rows) * 46
    dt = [f"drawtext=fontfile='{esc(FONT)}':textfile='{files[i]}':fontsize=76:fontcolor=white:borderw=6:bordercolor=black@0.85:x=(w-text_w)/2:y={y0 + i * 96}"
          for i in range(len(rows))]
    dt.append(f"drawbox=x=150:y={y0 + len(rows) * 96 + 40}:w=780:h=110:color=0xE2B877@0.97:t=fill")
    dt.append(f"drawtext=fontfile='{esc(FONT)}':textfile='{files[-1]}':fontsize=54:fontcolor=0x221D18:x=(w-text_w)/2:y={y0 + len(rows) * 96 + 68}")
    fc = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=brightness=-0.18:saturation=1.05,"
          f"drawbox=x=0:y=880:w=1080:h=900:color=black@0.35:t=fill,{','.join(dt)}[b];[1:v]scale=300:-1[lg];[b][lg]overlay=(W-w)/2:150")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(ROOT, "assets", "photos", photo + ".jpg"), "-i", LOGO,
                    "-filter_complex", fc, "-frames:v", "1", "-q:v", "2", out], check=True)


def upload_site(path, name):
    url = f"https://x-access-token:{os.environ['WEBSITE_TOKEN']}@github.com/mdeshlahra123/vajraformwork.git"
    d = os.path.join(ROOT, "work", "site-story")
    subprocess.run(["rm", "-rf", d]); subprocess.run(["git", "clone", "-q", "--depth", "1", url, d], check=True)
    subprocess.run(["cp", path, os.path.join(d, "social", name)], check=True)
    for c in (["git", "-C", d, "config", "user.name", "vajra-bot"], ["git", "-C", d, "config", "user.email", "vajra-bot@users.noreply.github.com"],
              ["git", "-C", d, "add", "social/" + name], ["git", "-C", d, "commit", "-qm", "story " + name], ["git", "-C", d, "push", "-q"]):
        subprocess.run(c, check=True)
    pub = "https://vajraformwork.vercel.app/social/" + name
    for _ in range(30):  # wait for Vercel
        time.sleep(10)
        try:
            if urllib.request.urlopen(urllib.request.Request(pub, method="HEAD"), timeout=20).status == 200:
                return pub
        except Exception:
            pass
    raise RuntimeError("story image not live on website")


def post_story(img_url):
    t = os.environ["META_TOKEN"]
    def call(path, **p):
        p["access_token"] = t
        return json.load(urllib.request.urlopen(urllib.request.Request(V + path, data=urllib.parse.urlencode(p).encode()), timeout=60))
    c = call(f"/{IG}/media", media_type="STORIES", image_url=img_url)
    for _ in range(20):
        time.sleep(6)
        st = json.load(urllib.request.urlopen(f"{V}/{c['id']}?fields=status_code&access_token={t}", timeout=30)).get("status_code")
        if st in ("FINISHED", "ERROR"):
            break
    return call(f"/{IG}/media_publish", creation_id=c["id"])["id"]


def main():
    s = load()
    kinds = list(TYPES)
    kind = kinds[s["n"] % len(kinds)]
    photo = next((p for p in random.sample(PHOTOS, len(PHOTOS)) if p not in s["photos"][-8:]), random.choice(PHOTOS))
    line = write_line(kind, photo, s["lines"])
    if kind in ("sawal", "ya") and not line.rstrip().endswith(("?", ".", "!")):
        line = line.rstrip() + "?"
    out = os.path.join(ROOT, "work", "story.jpg"); render(photo, line, ASK[kind], out)
    print("story", kind, photo, "|", line)
    if "--dry" in sys.argv:
        return
    stamp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%m%d-%H%M")
    url = upload_site(out, f"story-{stamp}.jpg")
    sid = post_story(url)
    print("STORY OK", sid, url)
    s["n"] += 1; s["photos"] = (s["photos"] + [photo])[-20:]; s["lines"] = (s["lines"] + [line])[-60:]
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
