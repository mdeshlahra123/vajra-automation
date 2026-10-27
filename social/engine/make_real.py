"""Turn real site clips (sent to the Telegram group) into a VAJRA reel.

python social/engine/make_real.py --clips <file_id,file_id,...> --note "..." --who Shobhit
Downloads the clips from Telegram, lets Gemini watch them and plan the edit (best parts, Hinglish voiceover,
on-screen text, caption, problems), edits with ffmpeg (voice + music + real site sound underneath, logo, end card),
then adds a pending item (real=True, position=alternate). Then run tg.py send <id>.
Needs: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, ffmpeg.
"""
import argparse, base64, datetime, json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import gem
from make_reel import A, FONT, W, H, FPS, TEXT_MODEL, MUSIC_MODEL, sh, dur, tts, mix

TG = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', '')}/"


def download(file_id, path):
    info = json.load(urllib.request.urlopen(TG + "getFile?file_id=" + file_id, timeout=60))
    if not info.get("ok"):
        raise RuntimeError(f"getFile failed (file too big? bots can only download up to 20 MB): {info}")
    fp = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{fp}"
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())


def has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def is_flow(note):
    return "flow" in (note or "").lower()


def plan(clips, note, who):
    rules = open(A("social", "engine", "brand.md"), encoding="utf-8").read()
    lens = ", ".join(f"clip {i}: {d:.1f}s" for i, (_, d) in enumerate(clips))
    flow = is_flow(note)
    src = ("AI-generated Google Flow clips (problem / site-mood shots; they show brown plywood problems or a site, NOT a real VAJRA demo). "
           "Use them as a problem-first story: open on the pain, build curiosity, reveal VAJRA PP shuttering sheet only in the LAST segment as the answer. "
           "NEVER describe an AI clip as a test, proof or real result (no throw/bend/nail/water proof). Do not call people in them customers") if flow else f"REAL site clips that {who} shot"
    prompt = f"""You edit an Instagram Reel for VAJRA from {src}. Brand rules (follow strictly):
{rules}

{who}'s note about the clips: "{note or 'no note'}"
Clip lengths: {lens}. The clips are attached in order (clip 0 first).

Watch the clips. Plan a 12-25 second reel from the best parts:
- 2 to 4 segments, each 2-7 seconds, taken from the clips (start/end in seconds inside that clip). Skip shaky, dark or useless parts.
- Segment 1 is the hook: the most striking moment, with a voiceover line that makes a contractor stop scrolling.
- Each segment: one Hinglish voiceover line (max 12 words) describing what is really shown; on-screen text in 2 short lines
  (each max 20 characters, plain ASCII letters/numbers/basic punctuation, no emoji, no Devanagari).
- Each voiceover line must describe ONLY what is visible in that segment (e.g. do not say "smooth finish" unless finished concrete is shown). General allowed claims (light, "sahi handling ke saath ply se 2-3 guna zyada chalti hai", waterproof; NEVER an exact number of uses/pours, never per-pour or yearly rupee maths) may go in at most one line. Never mention the sheet price.
- On-screen text in normal sentence case (e.g. "Column ready", not "COLUMN READY").
- Flag problems in "issues": a visible price, a competitor brand or logo, printed text on the sheet, unsafe work,
  faces of people who seem unaware of the camera, or footage too poor to use. ok=false if the reel should not be posted.

Return JSON only:
{{"ok": true, "issues": [], "title": "short internal title",
  "segments": [{{"clip": 0, "start": 0.0, "end": 4.0, "vo": "...", "text1": "...", "text2": "..."}}],
  "end_vo": "Comment mein PP likhiye, follow kijiye, rate aapke DM mein.",
  "caption": "Hinglish caption, 3-5 short lines, ends with the comment-PP line, Follow kijiye @vajraformwork, phone, hashtags from the rules"}}"""
    inp = [{"type": "text", "text": prompt}]
    for path, _ in clips:
        proxy = path.replace(".mp4", "-proxy.mp4")
        sh("ffmpeg", "-v", "error", "-y", "-i", path, "-vf", "scale=-2:360,fps=12", "-c:v", "libx264", "-crf", "32", "-preset", "veryfast",
           "-c:a", "aac", "-b:a", "48k", "-ac", "1", proxy)
        inp.append({"type": "video", "mime_type": "video/mp4", "data": base64.b64encode(open(proxy, "rb").read()).decode()})
    r = gem.interact(TEXT_MODEL, inp, response_format={"type": "text", "mime_type": "application/json"})
    p = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
    segs = []
    for s in p.get("segments", [])[:4]:
        c = int(s.get("clip", 0))
        if not 0 <= c < len(clips):
            continue
        d = clips[c][1]
        st = max(0.0, min(float(s.get("start", 0)), max(0.0, d - 1.5)))
        en = max(st + 1.5, min(float(s.get("end", st + 4)), d))
        for k in ("text1", "text2"):
            s[k] = re.sub(r"[^A-Za-z0-9 .,!?'+:/%-]", "", s.get(k, ""))[:22]
            if s[k].isupper(): s[k] = s[k].capitalize()
        s.update(clip=c, start=round(st, 2), end=round(en, 2)); segs.append(s)
    if not segs:
        segs = [{"clip": i, "start": 0.0, "end": min(5.0, d), "vo": "", "text1": "VAJRA PP", "text2": "Asli site"} for i, (_, d) in enumerate(clips[:3])]
    p["segments"] = segs
    import claims  # never promise a use count
    for s in segs:
        s["vo"] = claims.fix_line(s.get("vo", ""))
        for k in ("text1", "text2"):
            s[k] = claims.fix_line(s.get(k, ""), short=True)
    p["caption"] = claims.fix_caption(p.get("caption", ""))
    if re.search(r"3[, ]?500|per sheet", p.get("caption", "") + " ".join(s["vo"] for s in segs), re.I):
        p["ok"] = False; p.setdefault("issues", []).append("plan mentioned the price")
    return p


def render_segment(src, s, seconds, out, work, i, audio):
    t1, t2 = os.path.join(work, f"t1_{i}.txt"), os.path.join(work, f"t2_{i}.txt")
    open(t1, "w").write(s["text1"]); open(t2, "w").write(s["text2"])
    font = FONT.replace("\\", "/").replace(":", "\\:")
    v = (f"[0:v]trim=start={s['start']}:duration={seconds:.2f},setpts=PTS-STARTPTS,fps={FPS},split[pa][pb];"
         f"[pa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.08[bg];"
         f"[pb]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,"
         f"tpad=stop_mode=clone:stop_duration=10,"
         f"drawtext=fontfile='{font}':textfile='{t1}':fontsize=84:fontcolor=0x221D18:box=1:boxcolor=0xE7E2D8@0.95:boxborderw=20:x=70:y=250,"
         f"drawtext=fontfile='{font}':textfile='{t2}':fontsize=84:fontcolor=0x221D18:box=1:boxcolor=0xE2B877@0.97:boxborderw=20:x=70:y=380[m];"
         f"[1]scale=260:-1[lg];[m][lg]overlay=W-w-50:70,format=yuv420p[v]")
    if audio:
        a = f";[0:a]atrim=start={s['start']}:duration={seconds:.2f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad[a]"
        ain = []
    else:
        a = ";[2:a]aresample=48000,aformat=channel_layouts=stereo[a]"
        ain = ["-f", "lavfi", "-t", f"{seconds:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
    sh("ffmpeg", "-v", "error", "-y", "-i", src, "-i", A("assets", "brand", "logo.png"), *ain, "-filter_complex", v + a,
       "-map", "[v]", "-map", "[a]", "-t", f"{seconds:.2f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "19", "-preset", "medium",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True); ap.add_argument("--note", default=""); ap.add_argument("--who", default="Shobhit")
    a = ap.parse_args()
    rid = "reel-real-" + (datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)).strftime("%m%d-%H%M")
    work = A("work", rid); os.makedirs(work, exist_ok=True); log = []
    clips = []
    for i, fid in enumerate(x for x in a.clips.split(",") if x.strip()):
        raw = os.path.join(work, f"raw{i}.mp4"); download(fid.strip(), raw)
        clips.append((raw, dur(raw)))
    p = plan(clips, a.note, a.who)
    log.append(f"plan ok={p.get('ok')} issues={p.get('issues')}")
    lines = [s["vo"] for s in p["segments"]] + [p.get("end_vo") or "Comment mein PP likhiye, follow kijiye, rate aapke DM mein."]
    vo_files, vo_lens = [], []
    for i, line in enumerate(lines):
        f = os.path.join(work, f"vo{i}.wav")
        if line.strip():
            vo_lens.append(tts(line, f))
        else:
            sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.3", f); vo_lens.append(0.3)
        vo_files.append(f)
    parts, starts, t = [], [], 0.0
    for i, s in enumerate(p["segments"]):
        src = clips[s["clip"]][0]
        seconds = max(s["end"] - s["start"], vo_lens[i] + 0.5, 2.0)
        out = os.path.join(work, f"s{i}.mp4"); render_segment(src, s, seconds, out, work, i, has_audio(src))
        parts.append(out); starts.append(t); t += seconds
    card_len = max(3.0, vo_lens[-1] + 0.3); starts.append(t + 0.2); total = t + card_len
    card = os.path.join(work, "card.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-i", A("assets", "brand", "cta-card.mp4"), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-vf", f"tpad=stop_mode=clone:stop_duration=5,fps={FPS},format=yuv420p", "-map", "0:v", "-map", "1:a", "-t", f"{card_len:.2f}",
       "-c:v", "libx264", "-crf", "19", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", card)
    parts.append(card)
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    video = os.path.join(work, "video.mp4"); sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video)
    music = os.path.join(work, "music.mp3")
    try:
        r = gem.interact(MUSIC_MODEL, f"{int(total)+5} second upbeat modern Indian instrumental background track for a short construction site reel, "
                         "light dhol and percussion, positive and confident, steady beat, no vocals, no lyrics", response_format={"type": "audio"})
        gem.save_first(r, "audio", music)
    except Exception as e:
        log.append(f"music failed: {str(e)[:200]}"); music = None
    final = A("social", "media", f"{rid}.mp4"); os.makedirs(os.path.dirname(final), exist_ok=True)
    mix(video, vo_files, starts, total, music, final, bed=True)
    os.makedirs(A("social", "engine", "plans"), exist_ok=True)
    p.update(build_log=log, seconds=round(total, 1), note=a.note, who=a.who)
    json.dump(p, open(A("social", "engine", "plans", f"{rid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    sys.path.insert(0, A("social")); import caption_fix; p["caption"] = caption_fix.fix(p["caption"]); open(A("social", "captions", f"{rid}.txt"), "w", encoding="utf-8").write(p["caption"].strip())
    warn = "" if p.get("ok", True) else " ⚠️ CHECK: " + "; ".join(p.get("issues", []))[:300]
    pend_path = A("social", "pending.json")
    pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
    pend["items"].append({"id": rid, "title": f"{"Flow (AI) reel" if is_flow(a.note) else "Real reel"} from {a.who}: {p.get('title', '')} ({total:.0f}s){warn}",
                          "file": f"social/media/{rid}.mp4", "caption": f"captions/{rid}.txt", "position": "alternate",
                          **({"ai": True} if is_flow(a.note) else {"real": True}), "status": "draft"})
    json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("REEL", rid, f"{total:.1f}s", final); print("\n".join(log))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f: f.write(f"id={rid}\n")


if __name__ == "__main__":
    main()
