"""Animated text reel (owner, 12 Nov: motion graphics, no AI video credits). 9:16, ~20 s, no voice; music from assets/music.
Formats (rotates): galtiyan = "N mistakes" checklist that ticks; myth = myth -> struck through -> fact.
Background: a library clip (blurred, darkened, slow). Text: Archivo, VAJRA colours. Ends on the CTA card.
  python social/engine/text_reel.py [--format galtiyan|myth] [--out path] [--no-queue]
Content: Gemini free key (text only), claims-guarded; falls back to a fixed bank. Never prices or use-counts.
"""
import argparse, datetime, json, math, os, random, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from make_reel import A, FONT, sh, dur
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import claims

W, H, FPS = 1080, 1920, 30
NAVY, GOLD, WHITE, RED, GREEN = (19, 33, 58), (242, 179, 61), (255, 255, 255), (220, 53, 53), (52, 199, 89)
BANK = {
    # galtiyan = general site knowledge, REVIEWED by hand; never AI-written (a wrong tip would hurt the brand)
    "galtiyan": [{"title": "Shuttering ki 4 galtiyan", "items": ["Gila ply dobara lagana", "Cover block bhool jaana",
                  "Jaldi de-shuttering", "Curing mein kanjoosi"], "fix": "Sahi shuttering, mazboot dhalai"},
                 {"title": "Monsoon dhalai ki 4 galtiyan", "items": ["Barish mein concrete daalna", "Sheet ko dhakna bhoolna",
                  "Paani bharne dena", "Props check na karna"], "fix": "Mausam dekho, phir dhalai"},
                 {"title": "De-shuttering ki 4 galtiyan", "items": ["Props jaldi hatana", "Sheet ko patakna",
                  "Dhone mein der karna", "Sheet gandi hi rakhna"], "fix": "Dhyan se kholo, dho kar rakho"},
                 {"title": "Column dhalai ki 4 galtiyan", "items": ["Plumb check na karna", "Clamp dheela chhodna",
                  "Cover block bhoolna", "Ek saath bhari concrete"], "fix": "Check karo, phir dhalai karo"}],
    # myth facts = approved claims only (brand.md); never generated
    "myth": [{"myth": "PP sheet mein kil nahi lagti", "fact": "Kil (nail) achhe se pakadti hai, ply ki tarah"},
             {"myth": "Plastic sheet paani mein phool jaati hai", "fact": "PP sheet waterproof hai, phoolti nahi"},
             {"myth": "PP sheet bahut bhaari hoti hai", "fact": "Halki hai, ek aadmi aaram se utha leta hai"},
             {"myth": "Ek baar use ke baad bekaar", "fact": "Dho kar dobara use karo. Sahi handling ke saath ply se 2-3 guna zyada chalti hai"},
             {"myth": "PP sheet kaatna mushkil hai", "fact": "Normal cutter se ply ki tarah kat jaati hai"},
             {"myth": "Plastic se finish kharab aati hai", "fact": "Concrete finish smooth aati hai, column ekdum saaf"}],
}


def font(sz, bold=True):
    return ImageFont.truetype(FONT, int(sz))


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def spring(x, z=0.5, w=16.0):
    """closed-form underdamped spring step response (0 -> 1 with a little overshoot): pure function of time, no state."""
    if x <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + z * w / wd * math.sin(wd * x))


def clamp(x): return max(0.0, min(1.0, x))


def mix(a, b, k): return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class Beat:
    """beat grid of the music bed: every move starts on a beat (12 Nov: from the Opus 5.5 prompt collection, 'something happens on every beat')."""
    def __init__(self, bpm, off): self.bpm, self.off, self.d = bpm, off, 60.0 / bpm
    def at(self, n): return self.off + n * self.d


def content(fmt):
    if fmt in ("myth", "galtiyan"):   # fixed, reviewed lists only; rotate least recently used
        key = "myth" if fmt == "myth" else "title"
        st = A("social", "text-reel-state.json"); used = json.load(open(st)) if os.path.exists(st) else {}
        c = min(BANK[fmt], key=lambda x: used.get(x[key], ""))
        used[c[key]] = datetime.date.today().isoformat(); json.dump(used, open(st, "w"), indent=1)
        return c
    try:
        import gem
        q = ("Write one short Hinglish motion-graphics reel for Indian contractors (VAJRA PP shuttering brand, but the reel is "
             "general site knowledge). " + ("JSON {\"title\": max 28 chars, \"items\": 4 common site mistakes, each max 26 chars, "
             "\"fix\": closing line max 32 chars}" if fmt == "galtiyan" else
             "JSON {\"myth\": a common belief about plastic/PP shuttering, max 40 chars, \"fact\": the truth, max 60 chars}")
             + ". Rules: no prices, no numbers of uses, no guarantees, no other brands. Plain ASCII.")
        c = gem.text("gemini-3.5-flash-lite", q, json_mode=True)
        txt = json.dumps(c, ensure_ascii=False)
        if re.search(r"(?i)rs|₹|\d{2,}|guarantee", txt) or claims.bad(txt):
            raise ValueError("unsafe")
        if fmt == "galtiyan" and len(c.get("items", [])) >= 3:
            c["items"] = [i[:28] for i in c["items"][:4]]; return c
        if fmt == "myth" and c.get("myth") and c.get("fact"):
            return c
    except Exception as e:
        print("content fallback:", str(e)[:100])
    return random.choice(BANK[fmt])


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def bal(d, text, f, maxw):
    """wrap, then rebalance so the last line is never a single orphan word."""
    ls = wrap(d, text, f, maxw)
    if len(ls) == 2 and len(ls[1].split()) == 1 and len(ls[0].split()) > 1:
        ws = text.split(); h = (len(ws) + 1) // 2; ls = [" ".join(ws[:h]), " ".join(ws[h:])]
    return ls


def frame_galtiyan(c, t, B):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    n = len(c["items"]); tfix = B.at(6 + 4 * n + 1)
    # title: pops on beat 1 with a spring
    t1 = B.at(1); k = spring(t - t1); al = int(255 * clamp((t - t1) / 0.15)); tsz = 92
    while True:
        ft = font(tsz); lines = wrap(d, c["title"], ft, W - 200)
        if len(lines) == 2 and len(lines[1].split()) == 1 and len(lines[0].split()) > 1:
            ws = c["title"].split(); h = (len(ws) + 1) // 2; lines = [" ".join(ws[:h]), " ".join(ws[h:])]
        if len(lines) <= 2 or tsz <= 64: break
        tsz -= 6
    ft = font(tsz * (0.85 + 0.15 * k)); y = 300 + (1 - k) * 40
    for ln in lines:
        tw = d.textlength(ln, font=ft)
        d.rounded_rectangle([80 - 10, y - 14, 80 + tw + 28, y + 108], 14, fill=GOLD + (al,)); d.text((90, y), ln, font=ft, fill=NAVY + (al,)); y += 130
    y += 50; fi = font(62)
    grey = ease((t - tfix) / 0.35)   # once the fix lands, the mistakes go quiet (roles by meaning)
    for i, it in enumerate(c["items"]):
        t0 = B.at(6 + 4 * i); kk = spring(t - t0)
        if t < t0: break
        x0 = 80 + (1 - kk) * 200; a = int(255 * clamp((t - t0) / 0.12) * (1 - 0.55 * grey))
        d.rounded_rectangle([x0, y, W - 80, y + 120], 22, fill=(255, 255, 255, int(235 * clamp((t - t0) / 0.12) * (1 - 0.5 * grey))))
        col = mix(NAVY, (130, 140, 160), grey) + (a,)
        d.text((x0 + 40, y + 28), f"{i + 1}.", font=fi, fill=col)
        sz = 62
        while sz > 40 and d.textlength(it, font=font(sz)) > (W - 80 - 200) - (x0 + 120): sz -= 2
        d.text((x0 + 120, y + 60), it, font=font(sz), fill=col, anchor="lm")
        tx = B.at(8 + 4 * i); kx = spring(t - tx, 0.42, 20.0)   # the red X hits two beats after the item, with an impact ring
        if t >= tx:
            cx, cy, r = W - 150, y + 60, 34 * kx
            d.line([cx - r, cy - r, cx + r, cy + r], fill=RED + (255,), width=12); d.line([cx - r, cy + r, cx + r, cy - r], fill=RED + (255,), width=12)
            e = clamp((t - tx) / 0.35)
            if e < 1: d.ellipse([cx - 34 - 60 * e, cy - 34 - 60 * e, cx + 34 + 60 * e, cy + 34 + 60 * e], outline=RED + (int(220 * (1 - e)),), width=6)
        y += 150
    kf = spring(t - tfix)
    if t >= tfix:
        ff = font(66); yy = H - 520 + (1 - kf) * 90
        for ln in bal(d, c["fix"], ff, W - 200):
            tw = d.textlength(ln, font=ff) * (0.9 + 0.1 * kf)
            d.rounded_rectangle([(W - tw) / 2 - 30, yy - 12, (W + tw) / 2 + 30, yy + 90], 18, fill=GREEN + (int(245 * clamp((t - tfix) / 0.12)),))
            d.text((W / 2, yy + 39), ln, font=ff, fill=WHITE + (int(255 * clamp((t - tfix) / 0.12)),), anchor="mm"); yy += 110
    return im


def frame_myth(c, t, B):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fl = font(60); ff = font(72)
    m = ease((t - B.at(11)) / B.d)   # beat 11: the myth shrinks upward and greys out (it TRANSFORMS, no cut)
    k = spring(t - B.at(1), 0.45, 18.0)
    if t >= B.at(1):
        cx, cy, w, h = 205, 380, 250 * (0.6 + 0.4 * k), 100 * (0.6 + 0.4 * k)
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 16, fill=mix(RED, (110, 110, 120), m) + (255,))
        d.text((cx, cy), "MYTH", font=font(60 * (0.6 + 0.4 * k)), fill=WHITE + (255,), anchor="mm")
    t2 = B.at(2); k2 = spring(t - t2); msz = 84 - 34 * m; fm = font(msz); y = 470 - 10 * m + (1 - k2) * 60
    lines = bal(d, c["myth"], fm, W - 180); ks = ease((t - B.at(8)) / (1.5 * B.d))
    if t >= t2:
        col = mix(WHITE, (150, 150, 160), m) + (int(255 * clamp((t - t2) / 0.12)),)
        for ln in lines:
            d.text((90, y), ln, font=fm, fill=col); tw = d.textlength(ln, font=fm)
            if ks > 0: d.line([90, y + msz * 0.62, 90 + tw * ks, y + msz * 0.62], fill=RED + (255,), width=int(14 - 6 * m))
            y += msz * 1.3
    tf = B.at(12)
    if t >= tf:
        kf = spring(t - tf, 0.45, 18.0); cx, cy, w, h = 200, 640, 240 * (0.6 + 0.4 * kf), 100 * (0.6 + 0.4 * kf)
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 16, fill=GREEN + (255,))
        d.text((cx, cy), "FACT", font=font(60 * (0.6 + 0.4 * kf)), fill=WHITE + (255,), anchor="mm")
        fw = bal(d, c["fact"], ff, W - 180); words = []; yy = 740
        for ln in fw:
            x = 90
            for w_ in ln.split():
                words.append((x, yy, w_)); x += d.textlength(w_ + " ", font=ff)
            yy += 100
        for j, (x, yy, w_) in enumerate(words):   # one word per beat
            tj = B.at(13 + j); kj = spring(t - tj)
            if t >= tj: d.text((x, yy + (1 - kj) * 36), w_, font=ff, fill=GOLD + (int(255 * clamp((t - tj) / 0.1)),))
    return im


def build(fmt, out):
    c = content(fmt)
    os.makedirs(A("assets", "music"), exist_ok=True)
    music = sorted(f for f in os.listdir(A("assets", "music")) if f.endswith(".mp3"))
    if not music:   # one-time: a 60 s bed, kept and reused by every text reel (no more credits after this)
        import gem
        from make_reel import MUSIC_MODEL
        r = gem.interact(MUSIC_MODEL, "60 second upbeat modern Indian instrumental for a motion-graphics construction reel, punchy "
                         "percussion and light synth, confident, clear beat, no vocals", response_format={"type": "audio"})
        gem.save_first(r, "audio", A("assets", "music", "text-bed-1.mp3")); music = ["text-bed-1.mp3"]
    m = A("assets", "music", random.choice(music))
    import beats
    bpm, off = beats.beat_grid(m); B = Beat(bpm, off); print(f"beat grid: {bpm} bpm, first beat {off}s")
    if fmt == "galtiyan":
        T = B.at(6 + 4 * len(c["items"]) + 1 + 8)
    else:
        T = B.at(13 + len(c["fact"].split()) + 4)
    work = A("work", "text-" + fmt); os.makedirs(work, exist_ok=True)
    lib = json.load(open(A("assets", "clips", "library.json"), encoding="utf-8"))
    clips = [n for n in lib if os.path.exists(A("assets", "clips", n)) and lib[n].get("secs", 0) >= 6]
    bgc = A("assets", "clips", random.choice(clips))
    bg = os.path.join(work, "bg.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", bgc, "-t", f"{T:.2f}", "-vf",
       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=1.6*PTS,boxblur=18:2,eq=brightness=-0.32:saturation=0.7,fps={FPS}",
       "-an", "-c:v", "libx264", "-crf", "22", "-preset", "veryfast", bg)
    fd = os.path.join(work, "f"); os.makedirs(fd, exist_ok=True)
    fn = frame_galtiyan if fmt == "galtiyan" else frame_myth
    n = int(T * FPS)
    for i in range(n):
        fn(c, i / FPS, B).save(os.path.join(fd, f"{i:05d}.png"))
    ov = os.path.join(work, "ov.mov")
    sh("ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(fd, "%05d.png"), "-c:v", "qtrle", ov)
    body = os.path.join(work, "body.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-i", bg, "-i", ov, "-i", A("assets", "brand", "logo.png"), "-filter_complex",
       "[0][1]overlay=0:0[m];[2]scale=260:-1[lg];[m][lg]overlay=W-w-50:70,format=yuv420p[v]", "-map", "[v]", "-t", f"{T:.2f}",
       "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", body)
    card = os.path.join(work, "card.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-i", A("assets", "brand", "cta-card.mp4"), "-vf", f"tpad=stop_mode=clone:stop_duration=3,fps={FPS},format=yuv420p",
       "-t", "3.5", "-an", "-c:v", "libx264", "-crf", "20", card)
    lst = os.path.join(work, "l.txt"); open(lst, "w").write(f"file '{body}'\nfile '{card}'\n")
    vid = os.path.join(work, "v.mp4"); sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid)
    total = dur(vid)
    sh("ffmpeg", "-v", "error", "-y", "-i", vid, "-stream_loop", "-1", "-i", m, "-filter_complex",
       f"[1:a]atrim=0:{total:.2f},volume=0.8,afade=t=in:d=0.4,afade=t=out:st={total - 1.5:.2f}:d=1.5[a]", "-map", "0:v", "-map", "[a]",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", out)
    return c, total


def caption(fmt, c):
    head = c["title"] if fmt == "galtiyan" else ("Myth: " + c["myth"])
    body = ("Inme se aap kaunsi galti karte the? Comment mein number likhiye." if fmt == "galtiyan" else "Fact: " + c["fact"])
    cap = (f"{head}\n\n{body}\n\nVAJRA PP shuttering sheet: waterproof, halki, dho kar dobara use.\nComment mein PP likhiye, rate aapke DM mein. "
           "Follow kijiye @vajraformwork\n📞 83050 70160\n#PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors "
           "#Builders #Chhattisgarh #Raipur #Durg #Bhilai")
    return claims.fix_caption(cap)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--format", default=""); ap.add_argument("--out", default=""); ap.add_argument("--no-queue", action="store_true")
    a = ap.parse_args()
    ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
    fmt = a.format or ("galtiyan" if ist.isocalendar()[1] % 2 else "myth")
    rid = "reel-text-" + ist.strftime("%m%d-%H%M")
    out = a.out or A("social", "media", rid + ".mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    c, total = build(fmt, out)
    vol = subprocess.run(["ffmpeg", "-i", out, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mx = float(vol.split("max_volume:")[1].split("dB")[0]) if "max_volume:" in vol else -99
    print("TEXT REEL", rid, fmt, f"{total:.1f}s", f"max_volume {mx} dB", json.dumps(c, ensure_ascii=False))
    if mx < -60:
        raise SystemExit("silent text reel; not queued")
    if a.no_queue:
        return
    sys.path.insert(0, A("social")); import caption_fix
    open(A("social", "captions", rid + ".txt"), "w", encoding="utf-8").write(caption_fix.fix(caption(fmt, c)).strip())
    pend_path = A("social", "pending.json"); pend = json.load(open(pend_path, encoding="utf-8"))
    pend["items"].append({"id": rid, "title": f"Text reel ({fmt}): {c.get('title') or c.get('myth')} ({total:.0f}s)\n✅ Reviewer: text reel (no voice)",
                          "file": f"social/media/{rid}.mp4", "caption": f"captions/{rid}.txt", "position": "end", "real": True, "status": "draft"})
    json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    import library_reel; library_reel.queue_or_send(rid)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f: f.write(f"id={rid}\n")


if __name__ == "__main__":
    main()
