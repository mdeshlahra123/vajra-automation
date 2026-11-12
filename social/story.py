"""Daily Stories for Instagram AND Facebook (owner, 13 Nov: 'only insta? add facebook. same thing daily, make it engaging').
Runs in post.yml after each post (morning + evening). 7 formats, rotated so two stories on one day never look alike:
  quiz   2 frames  question with 3 options -> answer + reason
  poll   1 frame   split-screen 'PLY or PP', reply 1 / 2
  faq    2 frames  'aapne poocha' (real customer questions) -> answer
  myth   2 frames  MYTH struck through -> FACT
  tip    1 frame   one site tip on a real photo
  teaser 1 frame   'tonight 7:30' + the hook of the next queued reel
  clip   1 video   8 s real site clip with a caption (muted-friendly, soft music)
Content comes from reviewed banks (no AI-written site advice). Themes rotate (navy/gold, cream/red, green, black, gold).
API stories have no stickers, so every story asks for a reply (lands in DMs).
  python social/story.py            make + post one story (IG + FB)
  python social/story.py --dry      render only into work/stories/
  python social/story.py --dry --format quiz
Env: META_TOKEN, WEBSITE_TOKEN (to host the files), TELEGRAM_* optional.
"""
import datetime, json, os, random, re, subprocess, sys, time, urllib.parse, urllib.request
BASE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(BASE, "engine"))
from PIL import Image, ImageDraw, ImageFont
STATE = os.path.join(BASE, "story-state.json")
IG, PAGE, V = "17841424780649708", "1296793536861294", "https://graph.facebook.com/v24.0"
FONT = os.path.join(ROOT, "assets", "brand", "Archivo.ttf")
W, H = 1080, 1920
NAVY, GOLD, WHITE, CREAM, RED, GREEN, INK = (19, 33, 58), (242, 179, 61), (255, 255, 255), (244, 241, 234), (220, 53, 53), (52, 199, 89), (24, 24, 28)
THEMES = [
    {"bg": NAVY, "fg": WHITE, "accent": GOLD, "ink": NAVY, "logo": "logo.png"},
    {"bg": CREAM, "fg": NAVY, "accent": RED, "ink": WHITE, "logo": "logo-onlight.png"},
    {"bg": (20, 60, 50), "fg": WHITE, "accent": GOLD, "ink": (20, 60, 50), "logo": "logo.png"},
    {"bg": INK, "fg": WHITE, "accent": GREEN, "ink": INK, "logo": "logo.png"},
    {"bg": GOLD, "fg": NAVY, "accent": NAVY, "ink": GOLD, "logo": "logo-onlight.png"},
]
PHOTOS = ["slab-underside", "beam-box", "sheet-cut", "column-smooth2", "finish-column", "godown", "warehouse", "sheet-thin", "v5-cage", "v6-close", "v6-done", "p2-column"]
try:
    import add_photo as _ap; PHOTOS += list(_ap.extra())
except Exception:
    pass

QUIZ = [
    ("Ek VAJRA sheet ka wazan lagbhag kitna hai?", ["19 kg", "40 kg", "60 kg"], 0, "Halki hai, ek aadmi aaram se utha leta hai."),
    ("Kaunsi shuttering paani lagne par phool jaati hai?", ["Gila ply", "PP sheet", "Dono"], 0, "PP sheet waterproof hai, phoolti nahi."),
    ("VAJRA sheet ki motai kitni hai?", ["6 mm", "12 mm", "20 mm"], 1, "12 mm moti, aur 8 x 4 ft ki sheet."),
    ("PP sheet ko katne ke liye kya chahiye?", ["Normal cutter", "Laser machine", "Kat hi nahi sakti"], 0, "Ply ki tarah normal cutter se kat jaati hai."),
    ("Dhalai ke baad sheet ka kya karein?", ["Phenk dein", "Paani se dho kar rakhein", "Jala dein"], 1, "Dho kar dobara use karein. Finish bhi saaf aati hai."),
    ("Cover block kis liye lagate hain?", ["Saria ko concrete se dhakne ke liye", "Sirf sajaavat", "Shuttering hatane ke liye"], 0, "Saria ke charon taraf concrete ki parat rehti hai."),
    ("Curing kyun zaroori hai?", ["Nami dekar concrete mazboot banane ke liye", "Jaldi sukhane ke liye", "Sirf safai ke liye"], 0, "Nami milne se concrete ki taakat sahi banti hai."),
    ("PP sheet mein kil (nail) lagti hai?", ["Haan, achhe se pakadti hai", "Nahi lagti", "Sirf screw"], 0, "Ply ki tarah kil pakadti hai."),
    ("VAJRA sheet ka size kya hai?", ["6 x 3 ft", "8 x 4 ft", "10 x 5 ft"], 1, "8 x 4 ft, yaani ek sheet 32 sq ft."),
    ("De-shuttering mein sabse zaroori kya hai?", ["Jaldi karna", "Sahi samay par dheere kholna", "Sheet patakna"], 1, "Samay ke liye engineer se confirm karein."),
]
POLL = [("PLY", "PP SHEET", "Bhaari ply ya halki PP sheet?"), ("DHO KAR REUSE", "PHENK DO", "Dhalai ke baad sheet ka kya?"),
        ("ROUGH FINISH", "SMOOTH FINISH", "Aapko kaisa finish chahiye?"), ("EK AADMI", "CHAR AADMI", "Sheet uthane mein kitne log lagte hain?"),
        ("BARISH = BREAK", "KAAM CHALU", "Barish mein site pe kya hota hai?")]
FAQ = [("Is sheet ka naam kya hai?", "VAJRA PP hollow shuttering sheet. Ply ki jagah slab, beam, column aur wall mein use hoti hai."),
       ("Kis material ki bani hai?", "PP (polypropylene) plastic ki hollow sheet, light grey rang."),
       ("Kitne size mein milti hai?", "8 x 4 ft, 12 mm moti, wazan lagbhag 19 kg."),
       ("Kya paani se kharab hoti hai?", "Nahi. Waterproof hai, phoolti nahi."),
       ("Kya sample milta hai?", "Haan. 1 x 1 ft sample sirf 199/-, agle order mein adjust."),
       ("Kya bahar ke shehar mein bhejte hain?", "Haan, Chhattisgarh se poore India mein. Shehar + pincode WhatsApp karein."),
       ("Kitni chalti hai?", "Sahi handling ke saath ply se 2-3 guna zyada chalti hai."),
       ("Order kaise karein?", "WhatsApp karein 83050 70160: naam, shehar aur kitni sheet chahiye.")]
TIPS = ["Dhalai ke turant baad sheet paani se dho lo. Agli baar finish aur saaf aayegi.", "Sheet ko zameen pe ghaseet kar na le jayein, utha kar rakhein.",
        "Props lagane se pehle level zaroor check karein.", "Saria aur shuttering ke beech cover block lagana na bhoolein.",
        "Dhalai ki date barish ka forecast dekh kar tay karein.", "Curing shuru karne ki taareekh likh kar rakhein.",
        "Clamp aur kil poore ginti mein rakhein, site pe dhoondhne mein waqt na ganwayein.", "Mistri ko ek baar sheet katna aur jodna dikha dein, galti kam hogi."]
CAPTION = ["Aaj site se", "Dekhiye kaam", "Sheet in action", "Site ka ek pal", "Ready for dhalai"]
FORMATS = ["quiz", "clip", "poll", "faq", "myth", "teaser", "tip", "clip"]   # two a day: 2 neighbours differ in look


def F(sz): return ImageFont.truetype(FONT, int(sz))
def clamp(x): return max(0.0, min(1.0, x))


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines += [cur] if cur else []
    if len(lines) == 2 and len(lines[1].split()) == 1 and len(lines[0].split()) > 1:
        ws = text.split(); h = (len(ws) + 1) // 2; lines = [" ".join(ws[:h]), " ".join(ws[h:])]
    return lines


def fit(d, text, maxw, maxh, start, minsz=44, bold_gap=1.28):
    sz = start
    while sz > minsz:
        f = F(sz); ls = wrap(d, text, f, maxw)
        if len(ls) * sz * bold_gap <= maxh: return f, ls, sz
        sz -= 4
    f = F(minsz); return f, wrap(d, text, f, maxw), minsz


def base(theme, photo=None):
    if photo:
        p = Image.open(os.path.join(ROOT, "assets", "photos", photo + ".jpg")).convert("RGB")
        r = max(W / p.width, H / p.height); p = p.resize((int(p.width * r), int(p.height * r)))
        x, y = (p.width - W) // 2, (p.height - H) // 2; p = p.crop((x, y, x + W, y + H))
        im = Image.blend(p, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    else:
        im = Image.new("RGB", (W, H), theme["bg"])
        dark = Image.new("RGB", (W, H), tuple(int(c * 0.72) for c in theme["bg"]))
        im = Image.composite(dark, im, Image.linear_gradient("L").resize((W, H)))
        d = ImageDraw.Draw(im)
        for k in range(-H, W, 120):   # faint diagonal rule lines: a 'blueprint' feel
            d.line([(k, 0), (k + H, H)], fill=tuple(int(c * 0.9 + (255 - c) * 0.03) for c in theme["bg"]), width=2)
    lg = Image.open(os.path.join(ROOT, "assets", "brand", theme["logo"] if not photo else "logo.png")).convert("RGBA")
    lg = lg.resize((300, int(300 * lg.height / lg.width))); im.paste(lg, ((W - 300) // 2, 120), lg)
    return im


def pill(d, cx, y, text, f, fill, fg, padx=48, pady=22):
    tw = d.textlength(text, font=f); h = f.size + 2 * pady
    d.rounded_rectangle([cx - tw / 2 - padx, y, cx + tw / 2 + padx, y + h], h // 2, fill=fill)
    d.text((cx, y + h / 2), text, font=f, fill=fg, anchor="mm"); return y + h


def ask_bar(d, theme, text, y=1500):
    return pill(d, W / 2, y, text, F(52), theme["accent"], theme["ink"] if theme["accent"] != theme["bg"] else WHITE)


def centered(d, lines, f, y, fill, gap=1.28):
    for ln in lines:
        d.text((W / 2, y), ln, font=f, fill=fill, anchor="ma"); y += int(f.size * gap)
    return y


def f_quiz(theme, item, ans):
    q, opts, ok, why = item
    im = base(theme); d = ImageDraw.Draw(im)
    d.text((W / 2, 480), "ZARA SOCHIYE" if not ans else "SAHI JAWAB", font=F(56), fill=theme["accent"], anchor="ma")
    f, ls, sz = fit(d, q, W - 180, 330, 84); y = centered(d, ls, f, 560, theme["fg"]) + 50
    for i, o in enumerate(opts):
        good = ans and i == ok; dim = ans and i != ok
        col = GREEN if good else (theme["fg"] if theme["fg"] != WHITE else WHITE)
        fo = F(54); lines = wrap(d, o, fo, W - 400)
        hh = max(130, len(lines) * 66 + 50)
        d.rounded_rectangle([90, y, W - 90, y + hh], 30, fill=GREEN if good else ((255, 255, 255) if theme["fg"] == WHITE else (255, 255, 255)),
                            outline=None)
        d.ellipse([120, y + hh / 2 - 38, 196, y + hh / 2 + 38], fill=theme["bg"] if not good else WHITE)
        d.text((158, y + hh / 2), "ABC"[i], font=F(48), fill=WHITE if not good else GREEN, anchor="mm")
        ty = y + hh / 2 - (len(lines) - 1) * 33
        for ln in lines:
            d.text((230, ty), ln, font=fo, fill=WHITE if good else (150, 150, 158) if dim else NAVY, anchor="lm"); ty += 66
        y += hh + 26
    if ans:
        fw, ws, _ = fit(d, why, W - 200, 260, 56, 40); centered(d, ws, fw, y + 20, theme["fg"], 1.3)
        ask_bar(d, theme, "Reply karo PP: rate bhejte hain")
    else:
        ask_bar(d, theme, "Reply karo A / B / C")
    return im


def f_poll(theme, item):
    a, b, prompt = item
    im = base(theme); d = ImageDraw.Draw(im)
    f, ls, _ = fit(d, prompt, W - 160, 300, 84); y = centered(d, ls, f, 500, theme["fg"])
    top = max(y + 70, 800); bot = 1500
    d.rounded_rectangle([70, top, W / 2 - 15, bot], 44, fill=RED); d.rounded_rectangle([W / 2 + 15, top, W - 70, bot], 44, fill=GREEN)
    for cx, txt, n in ((W / 4 + 27, a, "1"), (3 * W / 4 - 27, b, "2")):
        d.text((cx, top + 150), n, font=F(190), fill=WHITE, anchor="mm")
        fo, lo, _ = fit(d, txt, 370, 300, 76, 40)
        yy = top + 330
        for ln in lo:
            d.text((cx, yy), ln, font=fo, fill=WHITE, anchor="ma"); yy += int(fo.size * 1.25)
    d.ellipse([W / 2 - 62, top + 90, W / 2 + 62, top + 214], fill=WHITE); d.text((W / 2, top + 152), "VS", font=F(54), fill=NAVY, anchor="mm")
    ask_bar(d, theme, "Reply karo 1 ya 2", 1560)
    return im


def f_faq(theme, item, ans, photo=None):
    q, a = item
    im = base(theme, photo); d = ImageDraw.Draw(im)
    fg = WHITE if photo else theme["fg"]
    d.text((W / 2, 480), "AAPNE POOCHA" if not ans else "JAWAB", font=F(58), fill=theme["accent"], anchor="ma")
    f, ls, _ = fit(d, q, W - 170, 420, 92); y = centered(d, ls, f, 580, fg)
    if ans:
        y += 50; d.rounded_rectangle([90, y, W - 90, y + 8], 4, fill=theme["accent"]); y += 60
        fa, la, _ = fit(d, a, W - 190, 560, 64, 44); centered(d, la, fa, y, fg, 1.32)
        ask_bar(d, theme, "Aur sawal? Reply karo")
    else:
        ask_bar(d, theme, "Jawab agli story mein")
    return im


def f_myth(theme, item, fact):
    m, t = item["myth"], item["fact"]
    im = base(theme); d = ImageDraw.Draw(im)
    y = pill(d, W / 2, 520, "MYTH", F(64), (150, 150, 160) if fact else RED, WHITE) + 50
    f, ls, _ = fit(d, m, W - 170, 360 if fact else 520, 92 if not fact else 66); mc = (150, 150, 160) if fact else theme["fg"]
    y0 = y
    for ln in ls:
        d.text((W / 2, y), ln, font=f, fill=mc, anchor="ma")
        if fact:
            tw = d.textlength(ln, font=f); d.line([(W - tw) / 2, y + f.size * 0.6, (W + tw) / 2, y + f.size * 0.6], fill=RED, width=10)
        y += int(f.size * 1.3)
    if fact:
        y += 70; y = pill(d, W / 2, y, "FACT", F(64), GREEN, WHITE) + 50
        ff, lf, _ = fit(d, t, W - 170, 520, 80, 48); centered(d, lf, ff, y, theme["accent"] if theme["accent"] not in (theme["bg"],) else theme["fg"], 1.3)
        ask_bar(d, theme, "Rate chahiye? Reply karo PP")
    else:
        ask_bar(d, theme, "Sach agli story mein")
    return im


def f_tip(theme, tip, photo):
    im = base(theme, photo); d = ImageDraw.Draw(im)
    pill(d, W / 2, 520, "AAJ KI TIP", F(58), theme["accent"], theme["ink"] if theme["accent"] != theme["bg"] else WHITE)
    f, ls, _ = fit(d, tip, W - 170, 640, 78, 50); centered(d, ls, f, 700, WHITE, 1.3)
    ask_bar(d, theme, "Aisi tips ke liye follow karo")
    return im


def f_teaser(theme, hook, slot):
    im = base(theme); d = ImageDraw.Draw(im)
    pill(d, W / 2, 520, "AAJ RAAT 7:30" if slot == "evening" else "AAJ SUBAH 9:30", F(66), RED, WHITE)
    d.text((W / 2, 760), "NAYI REEL", font=F(120), fill=theme["fg"], anchor="ma")
    d.text((W / 2, 900), "aa rahi hai", font=F(70), fill=theme["accent"], anchor="ma")
    f, ls, _ = fit(d, "\u201c" + hook + "\u201d", W - 180, 460, 70, 46); centered(d, ls, f, 1080, theme["fg"], 1.3)
    ask_bar(d, theme, "Dekhna mat bhoolna. Reply karo PP")
    return im


def clip_overlay(theme, caption, out):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 1180, W, H], fill=(0, 0, 0, 120))
    lg = Image.open(os.path.join(ROOT, "assets", "brand", "logo.png")).convert("RGBA"); lg = lg.resize((300, int(300 * lg.height / lg.width)))
    im.paste(lg, ((W - 300) // 2, 120), lg)
    f, ls, _ = fit(d, caption, W - 170, 300, 100); y = 1280
    for ln in ls:
        tw = d.textlength(ln, font=f); d.rounded_rectangle([(W - tw) / 2 - 28, y - 10, (W + tw) / 2 + 28, y + f.size + 24], 20, fill=theme["accent"] + (245,))
        d.text((W / 2, y + 6), ln, font=f, fill=theme["ink"] if theme["accent"] != theme["bg"] else WHITE, anchor="ma"); y += int(f.size * 1.35)
    pill(d, W / 2, 1640, "Rate chahiye? Reply karo PP", F(50), WHITE, NAVY)
    im.save(out)


def f_clip(theme, clip, caption, out):
    work = os.path.dirname(out); ov = os.path.join(work, "clip-ov.png"); clip_overlay(theme, caption, ov)
    path = os.path.join(ROOT, "assets", "clips", clip)
    secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip() or 8)
    ss = random.uniform(0, max(0.0, secs - 8.5)); music = os.path.join(ROOT, "assets", "music"); ms = sorted(f for f in os.listdir(music) if f.endswith(".mp3")) if os.path.isdir(music) else []
    ins = ["-ss", f"{ss:.2f}", "-t", "8", "-i", path, "-loop", "1", "-t", "8", "-i", ov]
    fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.1[bg];"
          f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0];"
          f"[1:v]format=rgba,fade=in:st=0.3:d=0.5:alpha=1[o];[v0][o]overlay=0:0,format=yuv420p[v]")
    cmd = ["ffmpeg", "-v", "error", "-y"] + ins
    if ms:
        cmd += ["-stream_loop", "-1", "-i", os.path.join(music, random.choice(ms))]
        fc += ";[2:a]atrim=0:8,volume=0.5,afade=t=in:d=0.3,afade=t=out:st=7:d=1[a]"; amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "128k"]
    else:
        amap = ["-an"]
    subprocess.run(cmd + ["-filter_complex", fc, "-map", "[v]"] + amap + ["-t", "8", "-r", "30", "-c:v", "libx264", "-crf", "24", "-preset", "veryfast",
                                                                          "-movflags", "+faststart", out], check=True)


def load():
    s = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    s.setdefault("n", 0); s.setdefault("photos", []); s.setdefault("lines", []); s.setdefault("used", {}); s.setdefault("last", "")
    return s


def lru(bank, key, s, name):
    d = s["used"].setdefault(name, {}); i = min(range(len(bank)), key=lambda k: (d.get(str(k), ""), k)); d[str(i)] = datetime.date.today().isoformat(); return bank[i]


def next_hook():
    try:
        sys.path.insert(0, os.path.join(BASE, "engine")); import claims
        q = json.load(open(os.path.join(BASE, "queue.json"), encoding="utf-8"))
        it = next((p for p in q["posts"] if not p.get("posted") and p.get("video")), None)
        if it:
            h = open(os.path.join(BASE, it["caption"]), encoding="utf-8").read().strip().split("\n")[0]
            h = claims.fix_line(h, short=False)
            return h[:110] if h else None
    except Exception:
        return None


def build(fmt, s, out_dir, slot):
    """returns [(kind, path)] frames for this format."""
    os.makedirs(out_dir, exist_ok=True); import usage
    th = lambda: random.choice(THEMES)
    frames = []
    if fmt == "quiz":
        it = lru(QUIZ, 0, s, "quiz"); t = th()
        for ans in (False, True):
            p = os.path.join(out_dir, f"f{len(frames)}.png"); f_quiz(t, it, ans).save(p); frames.append(("image", p))
    elif fmt == "poll":
        it = lru(POLL, 0, s, "poll"); p = os.path.join(out_dir, "f0.png"); f_poll(th(), it).save(p); frames.append(("image", p))
    elif fmt == "faq":
        it = lru(FAQ, 0, s, "faq"); t = th(); ph = usage.pick(PHOTOS)
        for ans in (False, True):
            p = os.path.join(out_dir, f"f{len(frames)}.png"); f_faq(t, it, ans, ph).save(p); frames.append(("image", p))
        s["photos"] = (s["photos"] + [ph])[-20:]; usage.mark(ph)
    elif fmt == "myth":
        sys.path.insert(0, os.path.join(BASE, "engine")); import text_reel
        it = lru(text_reel.BANK["myth"], 0, s, "myth"); t = th()
        for fact in (False, True):
            p = os.path.join(out_dir, f"f{len(frames)}.png"); f_myth(t, it, fact).save(p); frames.append(("image", p))
    elif fmt == "tip":
        tip = lru(TIPS, 0, s, "tip"); ph = usage.pick(PHOTOS); p = os.path.join(out_dir, "f0.png"); f_tip(th(), tip, ph).save(p); frames.append(("image", p))
        s["photos"] = (s["photos"] + [ph])[-20:]; usage.mark(ph)
    elif fmt == "teaser":
        h = next_hook()
        if not h:
            return build("poll", s, out_dir, slot)
        p = os.path.join(out_dir, "f0.png"); f_teaser(th(), h, slot).save(p); frames.append(("image", p))
    elif fmt == "clip":
        lib = json.load(open(os.path.join(ROOT, "assets", "clips", "library.json"), encoding="utf-8"))
        names = [n for n, v in lib.items() if not v.get("flow") and os.path.exists(os.path.join(ROOT, "assets", "clips", n)) and v.get("secs", 0) >= 6]
        c = usage.pick(names); p = os.path.join(out_dir, "f0.mp4"); f_clip(th(), c, random.choice(CAPTION), p); frames.append(("video", p)); usage.mark(c)
    return frames


def host(files):
    url = f"https://x-access-token:{os.environ['WEBSITE_TOKEN']}@github.com/mdeshlahra123/vajraformwork.git"
    d = os.path.join(ROOT, "work", "site-story")
    subprocess.run(["rm", "-rf", d]); subprocess.run(["git", "clone", "-q", "--depth", "1", url, d], check=True)
    for src, name in files:
        subprocess.run(["cp", src, os.path.join(d, "social", name)], check=True)
    for c in (["git", "-C", d, "config", "user.name", "vajra-bot"], ["git", "-C", d, "config", "user.email", "vajra-bot@users.noreply.github.com"],
              ["git", "-C", d, "add", "-A", "social"], ["git", "-C", d, "commit", "-qm", "stories"], ["git", "-C", d, "push", "-q"]):
        subprocess.run(c, check=True)
    urls = []
    for _, name in files:
        pub = "https://vajraformwork.vercel.app/social/" + name
        for _ in range(30):
            try:
                if urllib.request.urlopen(urllib.request.Request(pub, method="HEAD"), timeout=20).status == 200:
                    break
            except Exception:
                pass
            time.sleep(10)
        else:
            raise RuntimeError("not live: " + name)
        urls.append(pub)
    return urls


def _call(path, tok, **p):
    p["access_token"] = tok
    return json.load(urllib.request.urlopen(urllib.request.Request(V + path, data=urllib.parse.urlencode(p).encode()), timeout=120))


def ig_story(kind, url):
    t = os.environ["META_TOKEN"]
    c = _call(f"/{IG}/media", t, media_type="STORIES", **({"image_url": url} if kind == "image" else {"video_url": url}))
    for _ in range(40):
        time.sleep(6)
        st = json.load(urllib.request.urlopen(f"{V}/{c['id']}?fields=status_code&access_token={t}", timeout=30)).get("status_code")
        if st in ("FINISHED", "ERROR"):
            break
    return _call(f"/{IG}/media_publish", t, creation_id=c["id"])["id"]


def fb_story(kind, url):
    t = os.environ["META_TOKEN"]
    pt = json.load(urllib.request.urlopen(f"{V}/{PAGE}?fields=access_token&access_token={t}", timeout=30))["access_token"]
    if kind == "image":
        ph = _call(f"/{PAGE}/photos", pt, url=url, published="false")["id"]
        return _call(f"/{PAGE}/photo_stories", pt, photo_id=ph)
    st = _call(f"/{PAGE}/video_stories", pt, upload_phase="start")
    req = urllib.request.Request(st["upload_url"], data=b"", method="POST", headers={"Authorization": "OAuth " + pt, "file_url": url})
    print("FB upload:", urllib.request.urlopen(req, timeout=300).read()[:200])
    for _ in range(20):
        time.sleep(8)
        try:
            return _call(f"/{PAGE}/video_stories", pt, upload_phase="finish", video_id=st["video_id"])
        except urllib.error.HTTPError as e:
            print("FB finish retry:", e.read()[:150])
    raise RuntimeError("FB video story did not finish")


def main():
    s = load(); dry = "--dry" in sys.argv
    ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5); slot = "morning" if ist.hour < 14 else "evening"
    if "--format" in sys.argv:
        fmt = sys.argv[sys.argv.index("--format") + 1]
    else:
        order = [f for f in FORMATS]; fmt = order[s["n"] % len(order)]
        if fmt == s["last"]:
            fmt = order[(s["n"] + 1) % len(order)]
    out_dir = os.path.join(ROOT, "work", "stories"); subprocess.run(["rm", "-rf", out_dir]) if os.name != "nt" else None
    frames = build(fmt, s, out_dir, slot)
    print("story", fmt, [os.path.basename(p) for _, p in frames])
    if dry:
        return
    stamp = ist.strftime("%m%d-%H%M")
    files = [(p, f"story-{stamp}-{i}{'.mp4' if k == 'video' else '.jpg'}") for i, (k, p) in enumerate(frames)]
    for i, (k, p) in enumerate(frames):   # images -> jpg for hosting
        if k == "image":
            im = Image.open(p).convert("RGB"); jp = p.replace(".png", ".jpg"); im.save(jp, quality=92); files[i] = (jp, files[i][1])
    urls = host(files); ok = {"ig": 0, "fb": 0}
    for (k, _), u in zip(frames, urls):
        for plat, fn in (("ig", ig_story), ("fb", fb_story)):
            try:
                r = fn(k, u); ok[plat] += 1; print(plat.upper(), "STORY OK", k, str(r)[:80], flush=True)
            except Exception as e:
                body = e.read()[:200] if hasattr(e, "read") else b""
                print(plat.upper(), "STORY FAIL", k, str(e)[:120], body, flush=True)
        time.sleep(3)
    s["n"] += 1; s["last"] = fmt; json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("STORY DONE", fmt, ok)


if __name__ == "__main__":
    main()
