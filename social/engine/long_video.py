"""Weekly long educational video (owner, 11 Nov: earn from FB in-stream ads + YouTube long-form, VAJRA stays on the page).

  python social/engine/long_video.py plan [--topic N]   script + chapters + Flow brief (16:9 shots, use Extend) to Telegram
  python social/engine/long_video.py build --id ID      voice, visuals from the library (newest Flow clips first), music,
                                                        thumbnail, 2 vertical Shorts cut-downs; publish to YouTube + Facebook,
                                                        Shorts into the normal queue (IG / FB / YT Shorts)
  python social/engine/long_video.py build --id ID --no-publish
Format: 16:9 1280x720, 4-8 min, 5-7 chapters, first ad break after ~60 s (FB in-stream needs 3+ min).
Rules: brand.md + claims.py (no price, no use-count, only allowed claims), AI label (YouTube containsSyntheticMedia,
'AI visuals' tag on screen, line in the description). Free: Gemini text (free key), TTS/music on credits, ffmpeg.
"""
import argparse, datetime, json, os, re, subprocess, sys, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gem
from make_reel import A, FONT, sh, dur, tts, mix, MUSIC_MODEL
import claims

W, H, FPS = 1280, 720, 30
TEXT = "gemini-3.5-flash-lite"
STATE = A("social", "long-state.json")
LDIR = A("social", "engine", "long")
TOPICS = [
    "Monsoon mein ghar ka construction: slab dhalai, curing, shuttering aur material ki poori savdhani",
    "Slab dhalai step by step: shuttering se curing tak, site par sahi tarika",
    "Column shuttering kaise lagaye: saria cage se de-shuttering tak, common galtiyan",
    "Shuttering ki 7 galtiyan jo contractor ka paisa aur time barbaad karti hain",
    "De-shuttering kab karein: slab, beam, column ke liye sahi samay aur kyun",
    "Curing kitne din aur kyun: concrete ki mazbooti ka asli raaz",
    "Ply, steel aur PP shuttering: kaunsi kab use karein (fayde aur seemayein)",
    "Beam ki shuttering aur saria: site par hone wali aam galtiyan",
    "Ghar banwate waqt concrete ki quality kaise check karein: owner ke liye guide",
    "Contractor ka ek din: site par subah se shaam tak kya-kya hota hai",
]


def ist():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)


def ffmpeg(*a):
    sh("ffmpeg", "-v", "error", "-y", *a)


def tg(method, files=None, **p):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}"
    p["chat_id"] = os.environ["TELEGRAM_CHAT_ID"]
    if files:
        args = ["curl", "-s", url] + [x for k, v in p.items() for x in ("-F", f"{k}={v}")] + [x for k, f in files.items() for x in ("-F", f"{k}=@{f}")]
        return subprocess.run(args, capture_output=True, text=True).stdout
    return urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"}), timeout=60).read()


# ---------------------------------------------------------------- plan
def plan(topic):
    rules = open(A("social", "engine", "brand.md"), encoding="utf-8").read()
    q = f"""You write a long educational YouTube/Facebook video in Hinglish for VAJRA Formwork's page (PP shuttering sheets,
Chhattisgarh). Audience: Indian contractors, masons, engineers and house owners. The video must be GENUINELY USEFUL general
construction knowledge (not an advert). VAJRA appears only in the last chapter, briefly, as one option.
Topic: {topic}
Brand / claim rules (strict): {rules}
Extra rules: no prices, no exact number of uses, no invented statistics, no safety-critical numbers you are not sure of
(say "engineer se confirm karein" for structural specifics). Spoken natural Hinglish, like an experienced site engineer.
Structure (retention): chapter 1 = hook (25-35 s): the costly mistake / question, promise what they will learn.
Teaching chapters: one clear point each, a small open loop to the next chapter.
Last chapter (30-40 s): summary + soft VAJRA mention + "comment mein apna sawal likhiye, follow kijiye".
Then 5 teaching chapters, each 170-220 words (about 80 s spoken). The whole script MUST be at least 1,100 words (about 6 minutes; the voice reads ~3 words/second). Count carefully. Use examples from real sites to fill time usefully.
Also write 4-6 Google Flow shot prompts (16:9, realistic Indian construction site, no text/logos, no famous faces) that illustrate
the teaching chapters; each will be made 8 s and extended 2-3 times in Flow.
Return JSON only:
{{"title": "YouTube title, max 70 chars, curiosity + benefit, Hinglish", "thumb": ["THUMB LINE 1 max 16 chars", "line 2 max 16 chars"],
 "chapters": [{{"name": "short chapter title (max 30 chars)", "vo": "the full spoken text"}}],
 "flow_shots": ["prompt ..."],
 "description": "3-4 line Hinglish summary", "tags": ["10 search tags"],
 "shorts": [{{"chapter": 1, "hook": "first line for the short caption"}}, {{"chapter": 2, "hook": "..."}}]}}"""
    p = gem.text(TEXT, q, json_mode=True)
    for _ in range(2):   # 11 Nov test: 3.3 min came out; FB in-stream needs 3+ min, aim 5+
        words = sum(len(c["vo"].split()) for c in p["chapters"])
        if words >= 950:
            break
        x = gem.text(TEXT, "Expand every chapter's 'vo' of this video script so the total is at least 1,150 words. Add useful site "
                     "examples and explanations, keep the same rules and tone, keep VAJRA only in the last chapter. Return the same JSON "
                     "shape.\n" + json.dumps(p, ensure_ascii=False), json_mode=True)
        if x.get("chapters"):
            p["chapters"] = x["chapters"]
    print("script words:", sum(len(c["vo"].split()) for c in p["chapters"]))
    for c in p["chapters"]:   # claims guard, sentence by sentence
        c["vo"] = " ".join(claims.fix_line(s) for s in re.split(r"(?<=[.?!])\s+", c["vo"]) if s.strip())
        c["name"] = re.sub(r"[^A-Za-z0-9 .,!?'+:/&-]", "", re.sub(r"(?i)^\s*chapter\s*\d+\s*[:.-]\s*", "", c["name"]))[:34].strip()
    p["thumb"] = [re.sub(r"[^A-Za-z0-9 .,!?'+-]", "", t)[:18].upper() for t in p.get("thumb", [])][:2] or ["SITE KI", "BADI GALTI"]
    if re.search(r"(?i)₹|rs\.? ?\d|3[, ]?500|per sheet", json.dumps(p, ensure_ascii=False)):
        raise SystemExit("plan mentioned a price; rejected")
    return p


def flow_brief(lid, p):
    msg = (f"🎬 LONG VIDEO ({lid}): \"{p['title']}\"\nFlow mein 16:9 (landscape) chuniye. Har prompt: 8 sec banao, phir Extend karo, max ~30 sec (Flow ki limit). 720p download karke video ki tarah bhejo (file 20 MB se kam). "
           f"Bana ke yahin bhejo (caption ki zarurat nahi). Gurwaar ko video apne-aap banegi; jo clips aayengi wo use hongi, baaki library se.")
    tg("sendMessage", text=msg)
    for i, s in enumerate(p.get("flow_shots", [])[:6], 1):
        tg("sendMessage", text=f"{i}) {s}")


# ---------------------------------------------------------------- visuals
def library(since):
    clips = json.load(open(A("assets", "clips", "library.json"), encoding="utf-8"))
    photos = json.load(open(A("assets", "photos", "library.json"), encoding="utf-8"))
    import make_reel
    items = []
    for n, v in clips.items():
        if os.path.exists(A("assets", "clips", n)):
            items.append({"key": n, "kind": "clip", "ai": bool(v.get("flow")), "new": v.get("added", "") >= since,
                          "desc": (v.get("note") or n)[:120], "secs": v.get("secs", 6)})
    for k, d in make_reel.PHOTOS.items():
        if os.path.exists(A("assets", "photos", k + ".jpg")):
            items.append({"key": k, "kind": "photo", "ai": bool(photos.get(k, {}).get("ai")), "new": False, "desc": d[:120]})
    return items


def assign(p, items):
    lst = "\n".join(f"{i}. [{x['kind']}{' AI' if x['ai'] else ''}{' NEW' if x['new'] else ''}] {x['desc']}" for i, x in enumerate(items))
    q = (f"Pick visuals for each chapter of a construction education video from this library. Prefer NEW items (fresh Flow clips "
         f"made for this video) and clips over photos. Each chapter gets 3-6 different items that match what is said; an item may be "
         f"reused at most twice in the whole video. Brown plywood items only where ply is discussed.\nLibrary:\n{lst}\n\nChapters:\n"
         + "\n".join(f"{i}. {c['name']}: {c['vo'][:300]}" for i, c in enumerate(p["chapters"]))
         + '\nReturn JSON only: {"chapters": [[item numbers for chapter 0], [chapter 1], ...]}')
    try:
        r = gem.text(TEXT, q, json_mode=True)["chapters"]
        out = [[items[int(n)] for n in ch if 0 <= int(n) < len(items)] or items[:3] for ch in r][:len(p["chapters"])]
    except Exception as e:
        print("assign fallback:", e); out = []
    while len(out) < len(p["chapters"]):
        k = len(out); out.append([items[(k * 3 + j) % len(items)] for j in range(4)])
    return out


def render_item(x, seconds, out, title, ai_tag):
    """16:9 shot: any source fitted over its own blurred copy; photos get a slow zoom. Title shown first 4 s of a chapter."""
    font = FONT.replace("\\", "/").replace(":", "\\:")
    fr = int(seconds * FPS)
    bg = f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,eq=brightness=-0.12[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    if x["kind"] == "photo":
        src = ["-loop", "1", "-i", A("assets", "photos", x["key"] + ".jpg")]
        vf = bg + f",scale={W*2}:{H*2},zoompan=z='1.0+0.06*on/{fr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps={FPS}"
    else:
        src = ["-stream_loop", "-1", "-i", A("assets", "clips", x["key"])]
        vf = bg + f",fps={FPS}"
    txt = []
    if title:
        tf = out + ".t.txt"; open(tf, "w", encoding="utf-8").write(title)
        txt.append(f"drawtext=fontfile='{font}':textfile='{tf.replace(chr(92), '/').replace(':', chr(92) + ':')}':fontsize=46:fontcolor=0x13213A:box=1:boxcolor=0xF2B33D@0.96:boxborderw=16:x=48:y=48:enable='lt(t,4.5)'")
    if ai_tag:
        txt.append(f"drawtext=fontfile='{font}':text='AI visuals':fontsize=22:fontcolor=white@0.85:box=1:boxcolor=black@0.35:boxborderw=8:x=48:y=h-60")
    vf = vf + ("," + ",".join(txt) if txt else "")
    ffmpeg(*src, "-i", A("assets", "brand", "logo.png"), "-filter_complex", f"[0:v]{vf}[m];[1]scale=170:-1[lg];[m][lg]overlay=W-w-36:30,format=yuv420p[v]",
           "-map", "[v]", "-t", f"{seconds:.2f}", "-r", str(FPS), "-an", "-c:v", "libx264", "-crf", "24", "-preset", "veryfast", out)


def end_card(seconds, out):
    font = FONT.replace("\\", "/").replace(":", "\\:")
    ffmpeg("-f", "lavfi", "-i", f"color=c=0x13213A:s={W}x{H}:r={FPS}:d={seconds:.2f}", "-i", A("assets", "brand", "logo.png"), "-filter_complex",
           f"[1]scale=420:-1[lg];[0][lg]overlay=(W-w)/2:150,drawtext=fontfile='{font}':text='Comment mein apna sawal likhiye':fontsize=44:fontcolor=white:x=(w-tw)/2:y=430,"
           f"drawtext=fontfile='{font}':text='Call / WhatsApp  83050 70160':fontsize=40:fontcolor=0xF2B33D:x=(w-tw)/2:y=510,format=yuv420p[v]",
           "-map", "[v]", "-t", f"{seconds:.2f}", "-c:v", "libx264", "-crf", "24", "-preset", "veryfast", out)


def thumbnail(frame_src, lines, out):
    font = FONT.replace("\\", "/").replace(":", "\\:")
    d = ",".join(f"drawtext=fontfile='{font}':text='{l.replace(chr(39), '')}':fontsize=104:fontcolor=0x13213A:box=1:boxcolor=0xF2B33D:boxborderw=22:x=60:y={70 + i * 170}"
                 for i, l in enumerate(lines))
    ffmpeg("-ss", "2", "-i", frame_src, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.05:saturation=1.25,{d}",
           "-frames:v", "1", "-q:v", "2", out)   # frame already carries the logo


def cap_chunks(text, t0, dur):
    """sentences + their word counts + caption lines (~7 words) timed by word share of the voice line."""
    sents = [x for x in re.split(r"(?<=[.?!\u0964])\s+", text) if x.strip()] or [text]
    wc = [max(1, len(x.split())) for x in sents]; tot = sum(wc)
    out, t = [], t0
    for x, w in zip(sents, wc):
        d = dur * w / tot; ws = x.split(); n = max(1, round(len(ws) / 7)); per = len(ws) / n
        for k in range(n):
            out.append((t + d * k / n, t + d * (k + 1) / n, " ".join(ws[int(k * per):int((k + 1) * per)])))
        t += d
    return sents, wc, out


def load_wav(path):
    """16 kHz mono float32 via ffmpeg pipe (avoids PyAV version clashes on GitHub runners)."""
    import numpy as np, subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


_WM = None
def word_caps(wav, text, t0, dur):
    """11 Nov: captions timed to the real voice. faster-whisper gives word times; we keep the script's Hinglish words
    and map them onto the heard words by position. 4 words per caption. Falls back to cap_chunks on any error."""
    global _WM
    try:
        from faster_whisper import WhisperModel
        if _WM is None:
            _WM = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = _WM.transcribe(load_wav(wav), word_timestamps=True, language="hi")
        hw = [(float(w.start), float(w.end)) for sg in segs for w in sg.words]
        sw = text.split()
        if len(hw) < 3 or not sw:
            raise ValueError("no words heard")
        st = [hw[min(len(hw) - 1, int(i * len(hw) / len(sw)))][0] for i in range(len(sw))]
        caps = []
        for i in range(0, len(sw), 4):
            a = st[i]; b = st[i + 4] if i + 4 < len(sw) else min(dur, hw[-1][1] + 0.3)
            caps.append((t0 + a, t0 + max(b, a + 0.4), " ".join(sw[i:i + 4])))
        return caps
    except Exception as e:
        print("whisper timing fallback:", str(e)[:120])
        return cap_chunks(text, t0, dur)[2]


def write_srt(caps, path):
    f = lambda v: f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(v * 1000 % 1000):03d}"
    open(path, "w", encoding="utf-8").write("".join(f"{i}\n{f(a)} --> {f(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(caps, 1)))


def burn_captions(src, srt, dst):
    """white bold captions on a dark box near the bottom (libass, our Archivo font)."""
    style = ("FontName=Archivo,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=3,"
             "Outline=2,Shadow=0,MarginV=22,Alignment=2")
    fd = A("assets", "brand").replace("\\", "/").replace(":", "\\:")
    sp = srt.replace("\\", "/").replace(":", "\\:")
    try:
        ffmpeg("-i", src, "-vf", f"subtitles='{sp}':fontsdir='{fd}':force_style='{style}'", "-c:v", "libx264", "-crf", "23",
               "-preset", "veryfast", "-c:a", "copy", "-movflags", "+faststart", dst)
    except Exception as e:
        print("captions failed, publishing without:", str(e)[:150]); import shutil; shutil.copy(src, dst)


def build(lid, publish):
    p = json.load(open(os.path.join(LDIR, lid + ".json"), encoding="utf-8"))
    work = A("work", lid); os.makedirs(work, exist_ok=True)
    items = library(p.get("made", "2000-01-01")[:10])
    picks = assign(p, items)
    vo_files, starts, parts, chap_t, t = [], [], [], [], 0.0
    captions = []
    import polish
    for ci, c in enumerate(p["chapters"]):
        # 12 Nov: voice made ONE SENTENCE AT A TIME, so every sentence start is exact. Captions and picture cuts follow it.
        chap_t.append(t)
        sents = [x for x in re.split(r"(?<=[.?!\u0964])\s+", c["vo"]) if x.strip()] or [c["vo"]]
        sel = picks[ci]; tim = []
        for si, sent in enumerate(sents):
            f = os.path.join(work, f"vo{ci}_{si}.wav"); L = tts(sent, f)
            vo_files.append(f); starts.append(t); tim.append((t, L)); t += L + 0.25
        t += 0.6
        captions += polish.timed_chunks(sents, tim)
        n = max(1, min(len(sel), len(sents)))   # n picture groups, each a run of whole sentences
        for j in range(n):
            a = tim[j * len(sents) // n][0]; b = tim[(j + 1) * len(sents) // n][0] if j + 1 < n else t
            x = sel[j % len(sel)]
            d = (round(b * FPS) - round(a * FPS)) / FPS   # frame-exact boundaries: no drift over many pieces
            out = os.path.join(work, f"c{ci}_{j}.mp4"); render_item(x, d, out, c["name"] if j == 0 else "", x["ai"]); parts.append(out)
    t = round(t * FPS) / FPS
    card = os.path.join(work, "end.mp4"); end_card(6.0, card); parts.append(card); total = t + 6.0
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    video = os.path.join(work, "video.mp4"); ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video)
    music = os.path.join(work, "music.mp3"); loop = os.path.join(work, "music-loop.mp3")
    try:
        r = gem.interact(MUSIC_MODEL, "60 second calm, warm, modern Indian instrumental background for an educational construction video, "
                         "soft percussion and guitar, steady, unobtrusive, no vocals", response_format={"type": "audio"})
        gem.save_first(r, "audio", music)
        ffmpeg("-stream_loop", "-1", "-i", music, "-t", f"{total:.2f}", "-af", "volume=0.55", loop)
    except Exception as e:
        print("music failed:", str(e)[:150]); loop = None
    final = os.path.join(work, f"{lid}.mp4"); raw = os.path.join(work, "raw.mp4")
    mix(video, vo_files, starts, total, loop, raw)
    srt = os.path.join(work, "captions.srt"); write_srt(captions, srt); burn_captions(raw, srt, final)
    p["_captions"] = captions[:400]; p["_voice"] = list(zip(starts, [os.path.basename(v) for v in vo_files]))
    # check: sound and length
    vol = subprocess.run(["ffmpeg", "-i", final, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mx = float(vol.split("max_volume:")[1].split("dB")[0]) if "max_volume:" in vol else -99
    print(f"LONG {lid} {total/60:.1f} min, max_volume {mx} dB, {os.path.getsize(final)/1e6:.0f} MB")
    if mx < -60 or total < 200:
        raise SystemExit("long video failed checks (silent or under 3 min)")
    thumb = os.path.join(work, "thumb.jpg"); thumbnail(next((x for x in parts if "_0." in x), parts[0]), p["thumb"], thumb)
    chapters = "\n".join(f"{int(s // 60):02d}:{int(s % 60):02d} {c['name']}" for s, c in zip(chap_t, p["chapters"]))
    desc = (p.get("description", "") + "\n\nChapters:\n" + chapters + "\n\nVAJRA Formwork: PP shuttering sheet, Raipur / Durg / Bhilai, pan-India dispatch."
            "\nCall / WhatsApp: 83050 70160\nWebsite: https://vajraformwork.vercel.app\n\nVisuals include AI-generated footage (Google Flow) and real site footage.\n"
            "#construction #shuttering #civilengineering #housebuilding #slab #Chhattisgarh")
    shorts = make_shorts(lid, p, final, chap_t, total, work)
    res = {"seconds": round(total), "yt": None, "fb": None, "shorts": shorts}
    if publish:
        res["yt"] = yt_long(final, thumb, p, desc)
        res["fb"] = fb_long(final, thumb, p, desc)
        try:
            sys.path.insert(0, A("social")); import caption_fix
            igcap = caption_fix.fix(claims.fix_caption(p["title"] + "\n\n" + p.get("description", "") + "\n\nPoora video YouTube par bhi: https://youtu.be/" + str(res["yt"])
                    + "\n\nComment mein apna sawal likhiye. Follow kijiye @vajraformwork\n?? 83050 70160\n#PPFormwork #PlasticShuttering #Shuttering #Formwork "
                    "#Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai")).strip()
            res["ig"] = ig_long(final, igcap, True)
        except Exception as e:
            print("IG long failed:", str(e)[:200]); res["ig"] = None
        queue_shorts(lid, shorts)
        tg("sendMessage", text=f"📺 Long video live: \"{p['title']}\" ({total/60:.1f} min)\nYouTube: https://youtu.be/{res['yt']}\n"
           f"Facebook video: {res['fb']}\nInstagram: {'posted' if res.get('ig') else 'failed (retry later)'}\n+ {len(shorts)} shorts queue mein (IG/FB/YT Shorts).")
    else:
        tg("sendDocument", files={"document": thumb}, caption=f"Long video ready (not published): {p['title']} ({total/60:.1f} min)")
    p["result"] = res; p["built"] = ist().strftime("%Y-%m-%d %H:%M")
    json.dump(p, open(os.path.join(LDIR, lid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res


def ig_long(final, caption, publish=True):
    """Instagram long reel via the resumable upload (no public URL needed). 12 Nov test: Meta accepted a 6 min video; error 2207076
    is transient, so up to 4 fresh containers. Returns the media id (or 'ready:<container>' when publish=False)."""
    import time
    T = os.environ["META_TOKEN"]; IG = "17841424780649708"; V = "https://graph.facebook.com/v24.0/"
    size = os.path.getsize(final)
    def post(url, data, headers=None, timeout=240):
        req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode("utf-8", "replace")[:300]}
    for attempt in range(4):
        c = post(V + f"{IG}/media", urllib.parse.urlencode({"media_type": "REELS", "upload_type": "resumable", "caption": caption[:2150],
                 "share_to_feed": "true", "access_token": T}).encode())
        if "id" not in c or "uri" not in c:
            print("IG container failed:", c); time.sleep(30); continue
        print("IG container", c["id"], "uploading", size // 1000000, "MB", flush=True)
        try:
            up = post(c["uri"], open(final, "rb").read(), {"Authorization": "OAuth " + T, "offset": "0", "file_size": str(size),
                      "Content-Type": "application/octet-stream"}, timeout=600)
        except Exception as e:
            up = {"error": "upload exception: " + str(e)[:150]}
        print("IG upload:", str(up)[:200], flush=True)
        st = {}
        for _ in range(40):
            st = json.load(urllib.request.urlopen(V + f"{c['id']}?fields=status_code,status&access_token={T}", timeout=60))
            if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
                break
            time.sleep(15)
        print("IG status:", st.get("status_code"), st.get("status", "")[:100])
        if st.get("status_code") == "FINISHED":
            if not publish:
                return "ready:" + c["id"]
            r = post(V + f"{IG}/media_publish", urllib.parse.urlencode({"creation_id": c["id"], "access_token": T}).encode())
            print("IG publish:", r)
            return r.get("id")
        time.sleep(60)
    return None


def make_shorts(lid, p, final, chap_t, total, work):
    """2 vertical cut-downs (blurred-background 9:16) from chapters chosen by the plan, max 58 s each."""
    out = []
    font = FONT.replace("\\", "/").replace(":", "\\:")
    for k, s in enumerate(p.get("shorts", [])[:2]):
        ci = min(max(int(s.get("chapter", 1)), 0), len(chap_t) - 1)
        st = chap_t[ci]; en = min(chap_t[ci + 1] if ci + 1 < len(chap_t) else total - 6, st + 58)
        sid = f"{lid}-s{k+1}"; dst = A("social", "media", sid + ".mp4")
        tf = os.path.join(work, f"sh{k}.txt"); open(tf, "w", encoding="utf-8").write(p["chapters"][ci]["name"])
        ffmpeg("-ss", f"{st:.2f}", "-t", f"{en - st:.2f}", "-i", final, "-filter_complex",
               "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3[bg];"
               f"[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2,drawtext=fontfile='{font}':textfile='{tf.replace(chr(92), '/').replace(':', chr(92) + ':')}':fontsize=70:fontcolor=0x13213A:box=1:boxcolor=0xF2B33D:boxborderw=20:x=60:y=260,format=yuv420p[v]",
               "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst)
        cap = (s.get("hook") or p["chapters"][ci]["name"]) + "\n\nPoora video YouTube / Facebook par: " + p["title"] + \
              "\n\nComment mein apna sawal likhiye. Follow kijiye @vajraformwork\n📞 83050 70160\n" \
              "#PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai"
        sys.path.insert(0, A("social")); import caption_fix
        open(A("social", "captions", sid + ".txt"), "w", encoding="utf-8").write(caption_fix.fix(claims.fix_caption(cap)).strip())
        out.append(sid)
    return out


def queue_shorts(lid, shorts):
    pend_path = A("social", "pending.json"); pend = json.load(open(pend_path, encoding="utf-8"))
    for sid in shorts:
        pend["items"].append({"id": sid, "title": f"Edu short from long video {lid}", "file": f"social/media/{sid}.mp4",
                              "caption": f"captions/{sid}.txt", "position": "end", "ai": True, "status": "draft"})
    json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    import library_reel
    for sid in shorts:
        library_reel.queue_or_send(sid)


def yt_long(final, thumb, p, desc):
    sys.path.insert(0, A("social")); import yt_upload as y
    at = y.token(); data = open(final, "rb").read()
    body = {"snippet": {"title": p["title"][:95], "description": desc[:4900], "tags": (p.get("tags") or [])[:15] + ["VAJRA Formwork"],
                        "categoryId": "27", "defaultLanguage": "hi"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    req = urllib.request.Request(y.YT.replace("/youtube/v3/", "/upload/youtube/v3/") + "videos?uploadType=resumable&part=snippet,status",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))})
    loc = urllib.request.urlopen(req, timeout=60).headers["Location"]
    vid = json.load(urllib.request.urlopen(urllib.request.Request(loc, data=data, method="PUT", headers={"Content-Type": "video/mp4"}), timeout=1200))["id"]
    try:
        img = open(thumb, "rb").read()
        urllib.request.urlopen(urllib.request.Request(y.YT.replace("/youtube/v3/", "/upload/youtube/v3/") + f"thumbnails/set?videoId={vid}", data=img,
                               method="POST", headers={"Authorization": f"Bearer {at}", "Content-Type": "image/jpeg"}), timeout=60)
    except Exception as e:
        print("thumb skipped:", str(e)[:120])
    print("YT LONG", vid); return vid


def fb_long(final, thumb, p, desc):
    sys.path.insert(0, A("social", "agent")); import tools
    pt = tools.g(tools.PAGE, fields="access_token")["access_token"]
    r = subprocess.run(["curl", "-s", "-X", "POST", f"https://graph-video.facebook.com/v24.0/{tools.PAGE}/videos",
                        "-F", f"access_token={pt}", "-F", f"title={p['title'][:95]}", "-F", f"description={desc[:4900]}",
                        "-F", f"source=@{final}", "-F", f"thumb=@{thumb}"], capture_output=True, text=True, timeout=1800).stdout
    print("FB LONG", r[:200])
    try:
        return json.loads(r).get("id")
    except Exception:
        return None


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["plan", "build"]); ap.add_argument("--id", default="")
    ap.add_argument("--topic", type=int, default=-1); ap.add_argument("--no-publish", action="store_true")
    a = ap.parse_args(); os.makedirs(LDIR, exist_ok=True)
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": [], "last": ""}
    if a.mode == "plan":
        n = a.topic if a.topic >= 0 else next((i for i in range(len(TOPICS)) if i not in st["done"]), len(st["done"]) % len(TOPICS))
        lid = "long-" + ist().strftime("%m%d")
        p = plan(TOPICS[n]); p.update(topic=n, made=ist().strftime("%Y-%m-%d %H:%M"))
        json.dump(p, open(os.path.join(LDIR, lid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        st["done"].append(n); st["last"] = lid; json.dump(st, open(STATE, "w"), indent=1)
        flow_brief(lid, p); print("PLAN", lid, p["title"], [c["name"] for c in p["chapters"]])
    else:
        lid = a.id or st.get("last")
        if not lid:
            raise SystemExit("no plan to build")
        print(json.dumps(build(lid, not a.no_publish), ensure_ascii=False))


if __name__ == "__main__":
    main()
