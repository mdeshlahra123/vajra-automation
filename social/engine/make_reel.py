"""Make one VAJRA reel end to end on a GitHub runner.

python social/engine/make_reel.py [--brief "idea"] [--id reel-ai-xxx] [--res 720p]
Writes social/media/<id>.mp4, social/captions/<id>.txt, social/engine/plans/<id>.json
and adds a pending item to social/pending.json. Then run tg.py send <id>.
Needs: GEMINI_API_KEY, ffmpeg.
"""
import argparse, datetime, json, os, random, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import gem

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
A = lambda *p: os.path.join(ROOT, *p)
TEXT_MODEL, VIDEO_MODEL, TTS_MODEL, MUSIC_MODEL = "gemini-3.8-flash", "gemini-omni-1.1-flash", "gemini-3.8-flash-tts", "lyria-3.5"
VOICE, VOICE_STYLE = "Charon", "confident Indian male, natural Hinglish, warm and energetic, like a contractor explaining to a friend on site"
FONT = A("assets", "brand", "Archivo.ttf")
W, H, FPS = 1080, 1920, 30

PHOTOS = {
    "r-throw": "VAJRA sheet lying on the ground after being thrown from a roof, unbroken",
    "finish-column": "REAL finished concrete column just after VAJRA shuttering was removed, smooth and straight, bamboo props around (proof of finish)",
    "ply-pile": "pile of old broken brown plywood on a site (ONLY for ply-problem scenes)",
    "r-workers": "workers fixing VAJRA sheets around a column on site",
    "sheet-thin": "a full sheet standing upright on its edge outdoors, seen from above (shows it is thin and straight)",
    "v1-lean": "a VAJRA sheet lying flat on a site floor, close view",
    "v4-point": "person pointing at a VAJRA sheet",
    "v5-cage": "column steel cage ready, VAJRA panels being placed",
    "v6-close": "column fully closed with VAJRA panels and wooden battens",
    "v6-done": "workers holding a finished VAJRA column shuttering",
    "godown": "stacks of new VAJRA sheets on pallets in the godown",
    "p2-column": "tall column shuttered with VAJRA panels on a rooftop site",
    "warehouse": "large ready stock of VAJRA sheets in a warehouse",
    "slab-underside": "REAL slab underside fully shuttered with grey VAJRA sheets on a yellow steel frame (slab use)",
    "column-smooth2": "REAL smooth finished concrete column on site (proof of finish)",
    "beam-box": "REAL beam box: VAJRA sheets inside a red steel frame on site (beam use)",
    "sheet-cut": "REAL hand cutting a VAJRA sheet with a normal circular cutter (cuts easily, like wood)",
}
try:  # owners' Telegram photos, checked + added by add_photo.py
    import add_photo as _ap; PHOTOS.update(_ap.extra())
except Exception:
    pass
REFS = ["core-edge-grey.jpg", "sheet-held.jpg", "sheet-thin.jpg"]
SHEET = ("These must look exactly like the reference photos: VAJRA PP hollow shuttering sheet, a large flat 8 x 4 ft board "
         "(taller than a man when standing), 12 mm thick, plain light-grey faces, edge with SMALL round holes in two staggered rows. "
         "No text, no logos, no printing on anything.")


def sh(*args):
    r = subprocess.run(list(args), capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(" ".join(args)[:300] + "\n" + r.stderr[-1500:])
    return r.stdout + r.stderr


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def growth_note(past):
    """Angle + hooks to avoid from the growth loop (social/growth-plan.json). Owner 9 Nov: stop the same ply-problem reels."""
    avoid = list(past)
    try:
        g = json.load(open(A("social", "growth-plan.json"), encoding="utf-8"))
        n = len([f for f in os.listdir(A("social", "engine", "storyboards"))]) if os.path.isdir(A("social", "engine", "storyboards")) else 0
        angles = g.get("next_angles") or []
        angle = angles[n % len(angles)] if angles else ""
        avoid += g.get("avoid_hooks", [])
        ideas = " | ".join(g.get("hook_ideas", [])[:5])
    except Exception:
        angle, ideas = "", ""
    # owner 11 Nov: 3-4 non-sales posts a week for monetization. AI reels run Mon/Wed/Fri: Wed = educational, Fri = entertainment.
    day = (datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)).strftime("%A")
    if day == "Wednesday":
        return ("TYPE: EDUCATIONAL (not an advert). One genuinely useful construction site tip for contractors / house owners "
                "(curing, cover blocks, de-shuttering time, rain precautions, concrete check, common mistakes). Hook = the mistake or question. "
                "VAJRA is NOT the topic: no VAJRA scene; it appears only on the end card. Say 'engineer se confirm karein' for structural numbers.\n"
                "The hook must NOT resemble any of these recent hooks: " + " | ".join(h for h in avoid[:20] if h))
    if day == "Friday":
        return ("TYPE: ENTERTAINMENT (not an advert). A relatable, light, funny site-life moment (mazdoor bhai, contractor, chai break, "
                "owner visiting the site, monsoon chaos). Respectful humour, nobody mocked. At most one scene may show the grey VAJRA sheet "
                "naturally in the background. No selling lines.\n"
                "The hook must NOT resemble any of these recent hooks: " + " | ".join(h for h in avoid[:20] if h))
    out = (f"ANGLE for this reel (from our performance data, follow it): {angle}.\n" if angle else "")
    if angle and "ply" not in angle.lower():
        out += "Ply problems may appear at most in ONE scene, never as the hook.\n"
    if ideas:
        out += f"Fresh hook ideas you may use or adapt: {ideas}\n"
    return out + "The hook must NOT resemble any of these recent hooks: " + " | ".join(h for h in avoid[:20] if h)


def plan(brief, rid):
    rules = open(A("social", "engine", "brand.md"), encoding="utf-8").read()
    import usage
    ok = set(usage.fresh(PHOTOS)) | {"ply-pile"}
    photos = "\n".join(f"- {k}: {v}" for k, v in PHOTOS.items() if k in ok) or "\n".join(f"- {k}: {v}" for k, v in PHOTOS.items())
    past = []
    for f in sorted(os.listdir(A("social", "engine", "plans")))[-12:] if os.path.isdir(A("social", "engine", "plans")) else []:
        try: past.append(json.load(open(A("social", "engine", "plans", f), encoding="utf-8"))["hook"])
        except Exception: pass
    prompt = f"""You plan one Instagram Reel (vertical, 15-25 seconds) for VAJRA. Follow these rules strictly:
{rules}

Real photos you can use for proof scenes (use the key):
{photos}

Idea / brief: {brief or "Pick a strong idea that makes a contractor stop scrolling."}
{growth_note(past)}

Make exactly 3 scenes, ALL type "photo" (owner 11 Nov: free credits almost used up, no AI video generation).
The first scene is the hook: it grabs a contractor in 1 second and follows the ANGLE above (it does NOT have to be a ply problem).
Each scene: one voiceover line in Hinglish, max 12 words, natural spoken style; and on-screen text in 2 short lines
(normal sentence case, not all capitals; each max 20 characters, plain ASCII letters/numbers/basic punctuation only, no emoji, no Devanagari).
For "ai" scenes write a detailed English video prompt: single continuous shot, vertical, Indian construction site or godown,
real people, handheld phone look, natural light, no text anywhere, no dialogue.
IMPORTANT: a PROBLEM scene (heavy ply, broken ply, waste, cost) must show OLD BROWN WOODEN PLYWOOD only, with shows_vajra=false; never show the grey VAJRA sheet as the problem.
A SOLUTION scene shows the VAJRA sheet (shows_vajra=true); describe it as: {SHEET}

Return JSON only:
{{"hook": "...", "title": "short internal title",
  "scenes": [{{"type": "ai" or "photo", "photo": "key if photo", "video_prompt": "if ai", "shows_vajra": true or false, "vo": "...", "text1": "...", "text2": "..."}}],
  "end_vo": "Comment mein PP likhiye, follow kijiye, rate aapke DM mein.",
  "caption": "Hinglish caption, 3-5 short lines, ends with the comment-PP line, Follow kijiye @vajraformwork, phone, hashtags from the rules"}}"""
    p = gem.text(TEXT_MODEL, prompt, json_mode=True)
    p["scenes"] = p["scenes"][:3]
    ai = [s for s in p["scenes"] if s["type"] == "ai"]
    for s in ai[2:]:
        s.update(type="photo", photo="godown")
    for s in p["scenes"]:
        if s["type"] == "photo" and (s.get("photo") not in PHOTOS or s.get("photo") in ("r-used", "r-slab", "v2-used")):
            s["photo"] = random.choice(list(PHOTOS))
        for k in ("text1", "text2"):
            s[k] = re.sub(r"[^A-Za-z0-9 .,!?'+:/%-]", "", s.get(k, ""))[:22]
    # picture must match the words: a ply problem shows brown ply, a VAJRA line never shows the ply pile
    for s in p["scenes"]:
        if s.get("type") != "photo":
            continue
        words = " ".join(str(s.get(k, "")) for k in ("text1", "text2", "vo")).lower()
        about_ply = bool(re.search(r"\bply\b", words)) and not re.search(r"vajra|pp\b|panel|2-3 guna", words)
        if about_ply:
            s["photo"] = "ply-pile"
        elif s.get("photo") == "ply-pile":
            s["photo"] = "godown"
    import usage
    used_now = []
    for s in p["scenes"]:
        if s.get("type") == "photo" and s.get("photo") != "ply-pile" and usage.age(s["photo"]) < usage.COOLDOWN:
            s["photo"] = usage.pick([k for k in PHOTOS if k != "ply-pile"], avoid=used_now)
        if s.get("type") == "photo": used_now.append(s["photo"])
    import claims  # never promise a use count
    for s in p["scenes"]:
        for k in list(s):
            if isinstance(s[k], str) and k not in ("type", "photo"):
                s[k] = claims.fix_line(s[k], short=k.startswith("text"))
    for k in ("caption", "vo", "voice"):
        if isinstance(p.get(k), str):
            p[k] = claims.fix_caption(p[k])
    if re.search(r"3[, ]?500|per sheet", json.dumps(p), re.I):
        raise RuntimeError("plan mentions the price - refusing")
    return p


def tts(line, path):
    r = gem.interact(TTS_MODEL, [{"type": "user_input", "content": [{"type": "text", "text": line,
                     "annotations": [{"type": "speech_metadata", "style": VOICE_STYLE}]}]}],
                     response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": VOICE}]})
    gem.save_first(r, "audio", path)
    return dur(path)


def ai_clip(prompt, path, res, vajra=True):
    if vajra:
        inp = [{"type": "text", "text": prompt + " " + SHEET + " 6 seconds."}] + [gem.img_part(A("assets", "refs", f)) for f in REFS]
    else:
        inp = [{"type": "text", "text": prompt + " The boards are old brown wooden plywood: dirty, swollen, chipped edges. "
                "No grey or white plastic sheets anywhere. No text, no logos. 6 seconds."}]
    r = gem.interact(VIDEO_MODEL, inp, response_format={"type": "video", "aspect_ratio": "9:16", "resolution": res})
    gem.save_first(r, "video", path)


def check_clip(path, work, vajra=True):
    """Gemini looks at 4 frames; returns (ok, reason)."""
    frames = []
    d = dur(path)
    for i, t in enumerate((0.5, d * 0.35, d * 0.65, max(0.5, d - 0.4))):
        f = os.path.join(work, f"chk{i}.jpg"); sh("ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=-2:640", f); frames.append(f)
    q = ("These are 4 frames from an AI video ad for a plain light-grey plastic construction sheet. Answer JSON only: "
         '{"ok": true/false, "reason": "..."}. ok=false if ANY of: readable text, letters, logos or printing on the sheet or anywhere '
         "prominent; deformed hands, faces or bodies; obviously fake or glitchy frames."
         + (" Also ok=false if the sheet looks like wood, metal or a different product." if vajra
            else " These boards must be brown wooden plywood: ok=false if they look like grey or white plastic sheets."))
    r = gem.interact(TEXT_MODEL, [{"type": "text", "text": q}] + [gem.img_part(f) for f in frames], response_format={"type": "text", "mime_type": "application/json"})
    j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
    return bool(j.get("ok")), j.get("reason", "")


def scene_video(s, src, seconds, out, work, idx):
    t1, t2 = os.path.join(work, f"t1_{idx}.txt"), os.path.join(work, f"t2_{idx}.txt")
    open(t1, "w").write(s["text1"]); open(t2, "w").write(s["text2"])
    font = FONT.replace("\\", "/").replace(":", "\\:")
    txt = (f"drawtext=fontfile='{font}':textfile='{t1}':fontsize=84:fontcolor=0x221D18:box=1:boxcolor=0xE7E2D8@0.95:boxborderw=20:x=70:y=250,"
           f"drawtext=fontfile='{font}':textfile='{t2}':fontsize=84:fontcolor=0x221D18:box=1:boxcolor=0xE2B877@0.97:boxborderw=20:x=70:y=380")
    fr = int(seconds * FPS)
    if s["type"] == "photo":
        z = "1.02+0.08*on/%d" % fr if idx % 2 == 0 else "1.10-0.08*on/%d" % fr
        # fit the whole photo over a blurred copy of itself, so nothing (like the worker) gets cropped out
        vf = (f"split[pa][pb];[pa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.08[pbg];"
              f"[pb]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[pfg];[pbg][pfg]overlay=(W-w)/2:(H-h)/2,"
              f"scale={W*4}:{H*4}:flags=lanczos,setsar=1,"  # 4x first: zoompan rounds to whole pixels, so on a small frame the zoom shakes
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps={FPS},{txt}")
        inputs = ["-i", src]
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=10,{txt}"
        inputs = ["-i", src]
    sh("ffmpeg", "-v", "error", "-y", *inputs, "-i", A("assets", "brand", "logo.png"), "-filter_complex",
       f"[0:v]{vf}[m];[1]scale=260:-1[lg];[m][lg]overlay=W-w-50:70,format=yuv420p[v]", "-map", "[v]", "-t", f"{seconds:.2f}",
       "-r", str(FPS), "-an", "-c:v", "libx264", "-crf", "19", "-preset", "medium", out)


def build(p, rid, res):
    work = A("work", rid); os.makedirs(work, exist_ok=True)
    log = []
    # voice
    lines = [s["vo"] for s in p["scenes"]] + [p["end_vo"]]
    vo_files, vo_lens = [], []
    for i, line in enumerate(lines):
        f = os.path.join(work, f"vo{i}.wav"); vo_lens.append(tts(line, f)); vo_files.append(f)
    # scenes
    parts, starts, t = [], [], 0.0
    for i, s in enumerate(p["scenes"]):
        seconds = max(2.6, vo_lens[i] + 0.5)
        if s["type"] == "ai":   # 11 Nov money guard: never generate AI video; use a matching photo
            s.update(type="photo", photo=s.get("photo") or ("ply-pile" if not s.get("shows_vajra", True) else "godown"))
        if s["type"] == "ai":
            clip = os.path.join(work, f"ai{i}.mp4")
            for attempt in range(2):
                ai_clip(s["video_prompt"], clip, res, s.get("shows_vajra", True))
                ok, why = check_clip(clip, work, s.get("shows_vajra", True)); log.append(f"scene {i} ai attempt {attempt+1}: ok={ok} {why}")
                if ok: break
            else:
                log.append(f"scene {i}: AI clip failed check twice, using photo instead")
                s.update(type="photo", photo="godown")
        src = clip if s["type"] == "ai" else A("assets", "photos", s["photo"] + ".jpg")
        out = os.path.join(work, f"s{i}.mp4"); scene_video(s, src, seconds, out, work, i)
        parts.append(out); starts.append(t); t += seconds
    card = A("assets", "brand", "cta-card.mp4"); card_len = max(3.0, vo_lens[-1] + 0.3)
    starts.append(t + 0.2); total = t + card_len
    # end card stretched to fit end voiceover
    card_out = os.path.join(work, "card.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-i", card, "-vf", f"tpad=stop_mode=clone:stop_duration=5,fps={FPS},format=yuv420p", "-t", f"{card_len:.2f}", "-an", "-c:v", "libx264", "-crf", "19", card_out)
    parts.append(card_out)
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    video = os.path.join(work, "video.mp4"); sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video)
    # music
    music = os.path.join(work, "music.mp3")
    try:
        r = gem.interact(MUSIC_MODEL, f"{int(total)+5} second upbeat modern Indian instrumental background track for a short construction product ad, "
                         "light dhol and percussion, positive and confident, steady beat, no vocals, no lyrics", response_format={"type": "audio"})
        gem.save_first(r, "audio", music); has_music = True
    except Exception as e:
        log.append(f"music failed: {str(e)[:200]}"); has_music = False
    final = A("social", "media", f"{rid}.mp4"); os.makedirs(os.path.dirname(final), exist_ok=True)
    mix(video, vo_files, starts, total, music if has_music else None, final)
    try:   # 12 Nov: free polish (comment-box, PLY stamp on brown-ply scenes, voice-timed captions)
        import polish
        segs = [(starts[i], starts[i] + max(2.6, vo_lens[i] + 0.5), not s.get("shows_vajra", True)) for i, s in enumerate(p["scenes"])]
        log.append(polish.polish(final, lines, segs, list(zip(starts, vo_lens))))
    except Exception as e:
        log.append(f"polish skipped: {str(e)[:120]}")
    import usage; usage.mark(*[s.get("photo") for s in p["scenes"] if s.get("type") == "photo"])
    return final, total, log


def mix(video, vo_files, starts, total, music, final, bed=False):
    """voice lines at their scene starts, music ducked under voice, fade out.
    bed=True keeps the video's own sound (real site audio) quietly under everything."""
    ins, fc, labels = [], [], []
    for i, f in enumerate(vo_files):
        ins += ["-i", f]; ms = int(starts[i] * 1000 + 150)
        fc.append(f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]"); labels.append(f"[v{i}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad,atrim=0:{total:.2f}[vo]")
    under = None
    if music:
        n = len(vo_files) + 1; ins += ["-i", music]
        fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=0.32,afade=t=in:d=0.5,afade=t=out:st={total-1.5:.2f}:d=1.5[mu]")
        under = "[mu]"
    if bed:
        fc.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.22,apad,atrim=0:{total:.2f}[bed]")
        if under:
            fc.append("[mu][bed]amix=inputs=2:normalize=0[mb]"); under = "[mb]"
        else:
            under = "[bed]"
    if under:
        fc.append(f"[vo]asplit[vo1][vo2];{under}[vo1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];[duck][vo2]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    else:
        fc.append("[vo]anull[a]")
    sh("ffmpeg", "-v", "warning", "-y", "-i", video, *ins, "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", final)


def selftest():
    """mix() with synthetic inputs, no API calls."""
    w = A("work", "selftest"); os.makedirs(w, exist_ok=True)
    v = os.path.join(w, "v.mp4"); sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=320x568:r={FPS}:d=12", "-c:v", "libx264", v)
    vos = []
    for i, (f, d) in enumerate(((440, 2.5), (550, 3.0), (660, 2.0), (330, 3.0))):
        p = os.path.join(w, f"vo{i}.wav"); sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f={f}:d={d}", "-ar", "24000", "-ac", "1", p); vos.append(p)
    m = os.path.join(w, "m.mp3"); sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=30", "-ac", "2", m)
    out = os.path.join(w, "out.mp4"); mix(v, vos, [0, 3, 6.5, 9], 12.0, m, out)
    print("SELFTEST OK", dur(out))


def tg(method, files=None, **p):
    """Small Telegram call (multipart when a file is attached)."""
    import urllib.request, uuid
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}"
    p.setdefault("chat_id", os.environ["TELEGRAM_CHAT_ID"])
    if not files:
        req = urllib.request.Request(url, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    else:
        b = uuid.uuid4().hex; body = b""
        for k, v in p.items():
            body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v if isinstance(v, str) else json.dumps(v)}\r\n".encode()
        for k, path in files.items():
            body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{os.path.basename(path)}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + open(path, "rb").read() + b"\r\n"
        body += f"--{b}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def storyboard(p, rid):
    """Send the script + the photo/idea of every scene to Telegram. Nothing is made until an owner taps Banao."""
    tg("sendMessage", text=f"📝 Naya AI reel ka plan (abhi bana nahi). ID {rid}\nHook: {p['hook']}\nNeeche har scene ki photo/idea hai. Check karo.")
    for i, s in enumerate(p["scenes"], 1):
        cap = f"Scene {i}/{len(p['scenes'])}\nScreen: {s.get('text1', '')} / {s.get('text2', '')}\nAwaaz: {s.get('vo', '')}"
        if s["type"] == "photo":
            tg("sendPhoto", files={"photo": A("assets", "photos", s["photo"] + ".jpg")}, caption=cap)
        else:
            tg("sendMessage", text=cap + "\n🎬 AI video banega: " + s.get("video_prompt", "")[:600] +
               ("\n(VAJRA sheet dikhegi)" if s.get("shows_vajra") else "\n(sirf bhoora ply dikhega)"))
    tg("sendMessage", text=f"Caption:\n{p['caption'][:900]}\n\nAant: {p.get('end_vo', '')}\n\n"
       f"✅ Theek hai to 'Banao' dabao.\n✏️ Badlav chahiye to ISI message ka reply karo (jaise: 'pehle scene mein toota ply dikhao'). SB:{rid}",
       reply_markup={"inline_keyboard": [[{"text": "▶️ Banao", "callback_data": f"mk:{rid}"}, {"text": "❌ Chhodo", "callback_data": f"sb-no:{rid}"}]]})


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--brief", default=""); ap.add_argument("--id", default=""); ap.add_argument("--res", default="720p")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--mode", default="plan")  # plan | build | revise
    ap.add_argument("--feedback", default="")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    sbdir = A("social", "engine", "storyboards"); os.makedirs(sbdir, exist_ok=True)
    auto = a.mode == "auto"   # owner 9 Nov: autopilot, plan + build without the 'Banao' approval
    if auto:
        a.mode = "plan"
    if a.mode in ("plan", "revise"):
        if a.mode == "revise":
            old = json.load(open(os.path.join(sbdir, a.id + ".json"), encoding="utf-8"))
            brief = (old.get("brief", "") + "\n\nPREVIOUS PLAN (keep what is good):\n" + json.dumps({k: old[k] for k in ("hook", "scenes", "caption")}, ensure_ascii=False)
                     + "\n\nOWNER WANTS THESE CHANGES (must follow exactly):\n" + a.feedback)
            rid = a.id.split("-v")[0] + f"-v{int(a.id.split('-v')[1]) + 1 if '-v' in a.id else 2}"
        else:
            brief = a.brief
            rid = a.id or "reel-ai-" + (datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)).strftime("%m%d-%H%M")
        p = plan(brief, rid); p["brief"] = brief[:1500] if a.mode == "plan" else old.get("brief", "")
        json.dump(p, open(os.path.join(sbdir, rid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        if not auto:
            storyboard(p, rid); print("STORYBOARD", rid)
            return
        a.id = rid
    rid = a.id
    p = json.load(open(os.path.join(sbdir, rid + ".json"), encoding="utf-8"))
    final, total, log = build(p, rid, a.res)
    os.makedirs(A("social", "engine", "plans"), exist_ok=True)
    p["build_log"] = log; p["seconds"] = round(total, 1)
    json.dump(p, open(A("social", "engine", "plans", f"{rid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    sys.path.insert(0, A("social")); import caption_fix; p["caption"] = caption_fix.fix(p["caption"]); open(A("social", "captions", f"{rid}.txt"), "w", encoding="utf-8").write(p["caption"].strip())
    pend_path = A("social", "pending.json")
    pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
    pend["items"].append({"id": rid, "title": f"AI reel: {p.get('title', p['hook'])} ({total:.0f}s)", "file": f"social/media/{rid}.mp4",
                          "caption": f"captions/{rid}.txt", "position": "end", "ai": True, "status": "draft"})
    json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("REEL", rid, f"{total:.1f}s", final); print("\n".join(log))
    if auto:   # straight into the queue + FYI (no approval tap); see library_reel.queue_or_send
        import library_reel; library_reel.queue_or_send(rid)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f: f.write(f"id={rid}\n")


if __name__ == "__main__":
    main()
