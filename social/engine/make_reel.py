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
    "r-used": "close-up of a used VAJRA sheet edge next to broken old ply, after many pours",
    "r-throw": "VAJRA sheet lying on the ground after being thrown from a roof, unbroken",
    "r-slab": "underside of a full RCC slab shuttered with VAJRA sheets on a real site",
    "r-workers": "workers fixing VAJRA sheets around a column on site",
    "v1-core": "hand holding a sheet showing the hollow core edge",
    "v1-hold": "close-up of a hand gripping the thin edge of a sheet (shows it is thin, NOT a lifting shot)",
    "sheet-held": "a worker holding up a full 8x4 VAJRA sheet alone at the godown (best ONE-MAN-LIFT proof)",
    "sheet-thin": "a full sheet standing upright on its edge outdoors, seen from above (shows it is thin and straight)",
    "v1-lean": "a VAJRA sheet lying flat on a site floor, close view",
    "v4-point": "person pointing at a VAJRA sheet",
    "v5-cage": "column steel cage ready, VAJRA panels being placed",
    "v6-close": "column fully closed with VAJRA panels and wooden battens",
    "v6-done": "workers holding a finished VAJRA column shuttering",
    "godown": "stacks of new VAJRA sheets on pallets in the godown",
    "p2-column": "tall column shuttered with VAJRA panels on a rooftop site",
    "warehouse": "large ready stock of VAJRA sheets in a warehouse",
}
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


def plan(brief, rid):
    rules = open(A("social", "engine", "brand.md"), encoding="utf-8").read()
    photos = "\n".join(f"- {k}: {v}" for k, v in PHOTOS.items())
    past = []
    for f in sorted(os.listdir(A("social", "engine", "plans")))[-12:] if os.path.isdir(A("social", "engine", "plans")) else []:
        try: past.append(json.load(open(A("social", "engine", "plans", f), encoding="utf-8"))["hook"])
        except Exception: pass
    prompt = f"""You plan one Instagram Reel (vertical, 15-25 seconds) for VAJRA. Follow these rules strictly:
{rules}

Real photos you can use for proof scenes (use the key):
{photos}

Idea / brief: {brief or "Pick a strong idea that makes a contractor stop scrolling. Vary from these recent hooks: " + "; ".join(past)}

Make exactly 3 scenes. At most 2 scenes may be type "ai" (generated video); the rest are type "photo".
The first scene is the hook: a problem or question that grabs a contractor in 1 second.
Each scene: one voiceover line in Hinglish, max 12 words, natural spoken style; and on-screen text in 2 short lines
(each max 20 characters, plain ASCII letters/numbers/basic punctuation only, no emoji, no Devanagari).
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
        if s["type"] == "photo" and s.get("photo") not in PHOTOS:
            s["photo"] = random.choice(list(PHOTOS))
        for k in ("text1", "text2"):
            s[k] = re.sub(r"[^A-Za-z0-9 .,!?'+:/%-]", "", s.get(k, ""))[:22]
    if re.search(r"3[, ]?500|per sheet", json.dumps(p), re.I):
        raise RuntimeError("plan mentions the price - refusing")
    return p


def tts(line, path):
    r = gem.interact(TTS_MODEL, [{"type": "user_input", "content": [{"type": "text", "text": line,
                     "annotations": [{"type": "speech_metadata", "style": VOICE_STYLE}]}]}],
                     response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": VOICE}]})
    gem.save_first(r, "audio", path)
    return dur(path)


def ai_clip(prompt, path, res):
    refs = [gem.img_part(A("assets", "refs", f)) for f in REFS]
    inp = [{"type": "text", "text": prompt + " " + SHEET + " 6 seconds."}] + refs
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
        vf = (f"scale=1242:2208:force_original_aspect_ratio=increase:flags=lanczos,crop=1242:2208,setsar=1,"
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
    return final, total, log


def mix(video, vo_files, starts, total, music, final):
    """voice lines at their scene starts, music ducked under voice, fade out"""
    ins, fc, labels = [], [], []
    for i, f in enumerate(vo_files):
        ins += ["-i", f]; ms = int(starts[i] * 1000 + 150)
        fc.append(f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]"); labels.append(f"[v{i}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad,atrim=0:{total:.2f}[vo]")
    if music:
        n = len(vo_files) + 1; ins += ["-i", music]
        fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=0.32,afade=t=in:d=0.5,afade=t=out:st={total-1.5:.2f}:d=1.5[mu]")
        fc.append("[vo]asplit[vo1][vo2];[mu][vo1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];[duck][vo2]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--brief", default=""); ap.add_argument("--id", default=""); ap.add_argument("--res", default="720p")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rid = a.id or "reel-ai-" + (datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)).strftime("%m%d-%H%M")
    p = plan(a.brief, rid)
    final, total, log = build(p, rid, a.res)
    os.makedirs(A("social", "engine", "plans"), exist_ok=True)
    p["build_log"] = log; p["seconds"] = round(total, 1)
    json.dump(p, open(A("social", "engine", "plans", f"{rid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(A("social", "captions", f"{rid}.txt"), "w", encoding="utf-8").write(p["caption"].strip())
    pend_path = A("social", "pending.json")
    pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
    pend["items"].append({"id": rid, "title": f"AI reel: {p.get('title', p['hook'])} ({total:.0f}s)", "file": f"social/media/{rid}.mp4",
                          "caption": f"captions/{rid}.txt", "position": "end", "ai": True, "status": "draft"})
    json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("REEL", rid, f"{total:.1f}s", final); print("\n".join(log))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f: f.write(f"id={rid}\n")


if __name__ == "__main__":
    main()
