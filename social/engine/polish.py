"""Free reel polish (owner, 12 Nov). Runs on every finished reel, before review. Never breaks a build: on any error the
original file is kept.
  1. Effects (social/fx = claude-video-effects, MIT): Instagram comment box typing 'PP' near the end, VAJRA branding;
     reject stamp 'PLY' only over a scene that really shows brown ply (ply-problem scenes).
  2. Captions timed to the voice (faster-whisper word times, the script's own Hinglish words), burned near the bottom.
  polish(mp4, lines, segs) where lines = voice lines in order, segs = [(start, end, is_ply_scene), ...]
"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FX = os.path.join(ROOT, "social", "fx", "scripts", "fx.py")
FONTS = os.path.join(ROOT, "assets", "brand")
_WM = None


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip() or 0)


def fx_pass(src, dst, total, segs):
    plan = []
    s0 = max(0.0, total - 7.5)   # comment box over the last real scene, before the end card
    plan.append({"fx": "comment-box", "start": round(s0, 2), "end": round(min(total, s0 + 3.6), 2), "text": "PP",
                 "handle": "vajraformwork", "reply": "Rate aapke DM mein bhej diya", "chip": "PP shuttering"})
    for a, b, ply in segs:
        if ply and b - a > 1.6:
            plan.append({"fx": "reject-stamp", "start": round(a + 0.6, 2), "end": round(min(b, a + 2.2), 2), "text": "PLY"}); break
    pf = os.path.join(tempfile.mkdtemp(), "plan.json"); json.dump(plan, open(pf, "w"))
    r = subprocess.run([sys.executable, FX, "--plan", pf, src, dst], capture_output=True, text=True, timeout=1500)
    if r.returncode or not os.path.exists(dst):
        raise RuntimeError("fx failed: " + " | ".join((r.stderr or r.stdout).strip().splitlines()[-3:])[-300:])


def caption_pass(src, dst, lines):
    global _WM
    from faster_whisper import WhisperModel
    if _WM is None:
        _WM = WhisperModel("small", device="cpu", compute_type="int8")
    wav = os.path.join(tempfile.mkdtemp(), "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    segs, _ = _WM.transcribe(wav, word_timestamps=True, language="hi")
    hw = [(float(w.start), float(w.end)) for sg in segs for w in sg.words]
    sw = " ".join(lines).split()
    if len(hw) < 3 or not sw:
        raise RuntimeError("no words heard")
    st = [hw[min(len(hw) - 1, int(i * len(hw) / len(sw)))][0] for i in range(len(sw))]
    f = lambda v: f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(v * 1000 % 1000):03d}"
    srt, n, groups, k = [], 0, [], 0
    for sent in [x for l in lines for x in re.split(r"(?<=[.?!])\s+", l) if x.strip()]:   # chunks never cross a sentence
        ws = sent.split()
        for j in range(0, len(ws), 3):
            groups.append((k + j, min(k + j + 3, k + len(ws))))
        k += len(ws)
    for gi, (i, e) in enumerate(groups):
        a = st[min(i, len(st) - 1)]; b = st[e] if e < len(st) else hw[-1][1] + 0.3
        n += 1; srt.append(f"{n}\n{f(a)} --> {f(max(b, a + 0.35))}\n{' '.join(sw[i:e])}\n\n")
    sp = os.path.join(tempfile.mkdtemp(), "c.srt"); open(sp, "w", encoding="utf-8").write("".join(srt))
    style = ("FontName=Archivo,FontSize=15,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
             "Outline=3,Shadow=0,MarginV=70,Alignment=2")
    esc = lambda p: p.replace("\\", "/").replace(":", "\\:")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"subtitles='{esc(sp)}':fontsdir='{esc(FONTS)}':force_style='{style}'",
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)


def polish(mp4, lines, segs=()):
    """in place. Returns a short log line."""
    log = []
    total = dur(mp4); work = tempfile.mkdtemp(); cur = mp4
    try:
        a = os.path.join(work, "fx.mp4"); fx_pass(cur, a, total, segs); cur = a; log.append("fx ok")
    except Exception as e:
        log.append("fx skipped: " + str(e)[:120])
    try:
        b = os.path.join(work, "cap.mp4"); caption_pass(cur, b, [l for l in lines if l]); cur = b; log.append("captions ok")
    except Exception as e:
        log.append("captions skipped: " + str(e)[:120])
    if cur != mp4 and dur(cur) > total * 0.9:
        shutil.copy(cur, mp4)
    return "polish: " + ", ".join(log)


if __name__ == "__main__":
    print(polish(sys.argv[1], sys.argv[2:]))
