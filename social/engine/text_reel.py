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
    "galtiyan": [{"title": "Shuttering ki 4 galtiyan", "items": ["Gila ply dobara lagana", "Cover block bhool jaana",
                  "Jaldi de-shuttering", "Curing mein kanjoosi"], "fix": "Sahi shuttering, mazboot dhalai"},
                 {"title": "Monsoon dhalai ki 4 galtiyan", "items": ["Barish mein concrete daalna", "Sheet ko dhakna bhoolna",
                  "Paani bharne dena", "Props check na karna"], "fix": "Mausam dekho, phir dhalai"}],
    "myth": [{"myth": "Plastic shuttering kamzor hoti hai", "fact": "PP sheet concrete ka load uthati hai, sahi support ke saath"},
             {"myth": "PP sheet mein kil nahi lagti", "fact": "Kil (nail) achhe se pakadti hai, ply ki tarah"}],
}


def font(sz, bold=True):
    return ImageFont.truetype(FONT, int(sz))


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def content(fmt):
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


def frame_galtiyan(c, t, T):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    k = ease(t / 0.5); tsz = 92
    while True:
        ft = font(tsz); lines = wrap(d, c["title"], ft, W - 200)
        if len(lines) == 2 and len(lines[1].split()) == 1 and len(lines[0].split()) > 1:   # move a word down: no orphan
            ws = c["title"].split(); h = (len(ws) + 1) // 2; lines = [" ".join(ws[:h]), " ".join(ws[h:])]
        if len(lines) <= 2 or tsz <= 64: break
        tsz -= 6
    y = 300 - (1 - k) * 80
    for ln in lines:
        tw = d.textlength(ln, font=ft)
        d.rounded_rectangle([80 - 10, y - 14, 80 + tw + 28, y + 108], 14, fill=GOLD + (int(255 * k),))
        d.text((90, y), ln, font=ft, fill=NAVY + (int(255 * k),)); y += 130
    y += 50; fi = font(62)
    for i, it in enumerate(c["items"]):
        t0 = 1.6 + i * 2.6; kk = ease((t - t0) / 0.35)
        if kk <= 0: break
        x0 = 80 + (1 - kk) * 120; a = int(255 * kk)
        d.rounded_rectangle([x0, y, W - 80, y + 120], 22, fill=(255, 255, 255, int(235 * kk)))
        d.text((x0 + 40, y + 28), f"{i + 1}.", font=fi, fill=NAVY + (a,))
        sz = 62
        while sz > 40 and d.textlength(it, font=font(sz)) > (W - 80 - 200) - (x0 + 120): sz -= 2
        fz = font(sz); d.text((x0 + 120, y + 60), it, font=fz, fill=NAVY + (a,), anchor="lm")
        kx = ease((t - t0 - 1.0) / 0.25)   # red X mark draws in
        if kx > 0:
            cx, cy, r = W - 150, y + 60, 34 * kx
            d.line([cx - r, cy - r, cx + r, cy + r], fill=RED + (255,), width=12); d.line([cx - r, cy + r, cx + r, cy - r], fill=RED + (255,), width=12)
        y += 150
    tf = 1.6 + len(c["items"]) * 2.6 + 0.4; kf = ease((t - tf) / 0.4)
    if kf > 0:
        ff = font(66); ls = wrap(d, c["fix"], ff, W - 200); yy = H - 520 + (1 - kf) * 60
        for ln in ls:
            tw = d.textlength(ln, font=ff); d.rounded_rectangle([(W - tw) / 2 - 30, yy - 12, (W + tw) / 2 + 30, yy + 90], 18, fill=GREEN + (int(240 * kf),))
            d.text(((W - tw) / 2, yy), ln, font=ff, fill=WHITE + (int(255 * kf),)); yy += 110
    return im


def frame_myth(c, t, T):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fl, fm, ff = font(60), font(84), font(72)
    k = ease(t / 0.4); d.rounded_rectangle([80, 330, 330, 430], 16, fill=RED + (int(255 * k),)); d.text((112, 342), "MYTH", font=fl, fill=WHITE + (int(255 * k),))
    y = 480
    lines = wrap(d, c["myth"], fm, W - 180); ks = ease((t - 2.6) / 0.5)
    for ln in lines:
        d.text((90, y), ln, font=fm, fill=WHITE + (int(255 * k),)); tw = d.textlength(ln, font=fm)
        if ks > 0: d.line([90, y + 52, 90 + tw * ks, y + 52], fill=RED + (255,), width=14)
        y += 110
    kf = ease((t - 4.2) / 0.45)
    if kf > 0:
        y += 90; d.rounded_rectangle([80, y, 320, y + 100], 16, fill=GREEN + (int(255 * kf),)); d.text((112, y + 12), "FACT", font=fl, fill=WHITE + (int(255 * kf),))
        y += 150
        for ln in wrap(d, c["fact"], ff, W - 180):
            d.text((90, y + (1 - kf) * 40), ln, font=ff, fill=GOLD + (int(255 * kf),)); y += 100
    return im


def build(fmt, out):
    c = content(fmt)
    T = (1.6 + len(c["items"]) * 2.6 + 3.2) if fmt == "galtiyan" else 9.5
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
        fn(c, i / FPS, T).save(os.path.join(fd, f"{i:05d}.png"))
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
    os.makedirs(A("assets", "music"), exist_ok=True)
    music = sorted(f for f in os.listdir(A("assets", "music")) if f.endswith(".mp3"))
    if not music:   # one-time: a 60 s bed, kept and reused by every text reel (no more credits after this)
        import gem
        from make_reel import MUSIC_MODEL
        r = gem.interact(MUSIC_MODEL, "60 second upbeat modern Indian instrumental for a motion-graphics construction reel, punchy "
                         "percussion and light synth, confident, clear beat, no vocals", response_format={"type": "audio"})
        gem.save_first(r, "audio", A("assets", "music", "text-bed-1.mp3")); music = ["text-bed-1.mp3"]
    m = A("assets", "music", random.choice(music))
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
