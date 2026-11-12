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


def load_wav(path):
    """16 kHz mono float32 via ffmpeg pipe (avoids PyAV version clashes on GitHub runners)."""
    import numpy as np, subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


TAPE = [(r"waterproof|paani", "WATERPROOF"), (r"halk|utha|light", "HALKI SHEET"), (r"nail|kil\b", "KIL PAKADTI"),
        (r"cut|kat", "CUTTER SE KATTI"), (r"dho|wash|reuse", "DHO KAR REUSE"), (r"smooth|finish", "SMOOTH FINISH"),
        (r"ek aadmi|one man", "EK AADMI KAAFI")]


def fx_pass(src, dst, total, segs):
    """12 Nov: effects from claude-video-effects, placed by scene meaning and away from our own text:
    huge-strike 'PLY' on the first brown-ply scene; tape-label with the claim of up to two VAJRA scenes (lower-middle,
    above the captions, below the headline boxes); comment-box on the end card. segs = (start, end, is_ply[, voice line])."""
    plan, tapes, struck = [], 0, False
    for sg in segs:
        a, b, ply = sg[0], sg[1], sg[2]; vo = (sg[3] if len(sg) > 3 else "").lower()
        if b - a < 2.0:
            continue
        st, en = round(a + 0.7, 2), round(min(b - 0.2, a + 2.9), 2)
        if ply and not struck:
            plan.append({"fx": "huge-strike", "start": st, "end": en, "text": "PLY"}); struck = True
        elif not ply and tapes < 2:
            word = next((w for rx, w in TAPE if re.search(rx, vo)), None)
            if word:
                plan.append({"fx": "tape-label", "start": st, "end": en, "text": word}); tapes += 1
    s0 = max(0.0, total - 3.6)   # comment box on the end card, never over a scene headline
    plan.append({"fx": "comment-box", "start": round(s0, 2), "end": round(total, 2), "text": "PP",
                 "handle": "vajraformwork", "reply": "Rate aapke DM mein bhej diya", "chip": "PP shuttering"})
    pf = os.path.join(tempfile.mkdtemp(), "plan.json"); json.dump(plan, open(pf, "w"))
    r = subprocess.run([sys.executable, FX, "--plan", pf, src, dst], capture_output=True, text=True, timeout=1500)
    if r.returncode or not os.path.exists(dst):
        raise RuntimeError("fx failed: " + " | ".join((r.stderr or r.stdout).strip().splitlines()[-3:])[-300:])
    return [d["fx"] for d in plan]


def whisper_chunks(src, lines):
    global _WM
    from faster_whisper import WhisperModel
    if _WM is None:
        _WM = WhisperModel("small", device="cpu", compute_type="int8")
    wav = os.path.join(tempfile.mkdtemp(), "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    segs, _ = _WM.transcribe(load_wav(wav), word_timestamps=True, language="hi")
    hw = [(float(w.start), float(w.end)) for sg in segs for w in sg.words]
    sw = " ".join(lines).split()
    if len(hw) < 3 or not sw:
        raise RuntimeError("no words heard")
    st = [hw[min(len(hw) - 1, int(i * len(hw) / len(sw)))][0] for i in range(len(sw))]
    out, k = [], 0
    for sent in [x for l in lines for x in re.split(r"(?<=[.?!])\s+", l) if x.strip()]:
        n = len(sent.split())
        for j in range(0, n, 3):
            a, e = k + j, min(k + j + 3, k + n)
            out.append((st[min(a, len(st) - 1)], st[e] if e < len(st) else hw[-1][1] + 0.3, " ".join(sw[a:e])))
        k += n
    return out

def timed_chunks(lines, timing):
    """Exact sync (12 Nov fix): each voice line starts where the builder placed it (start + 0.15 s mix delay) and lasts its
    TTS length. Inside a line, words are spaced by their length. Chunks of max 3 words, never across a sentence."""
    out = []
    for line, (st, ln) in zip(lines, timing):
        if not line or not line.strip():
            continue
        st += 0.15; ln = max(0.6, ln - 0.25)
        ws = line.split(); tot = sum(len(w) + 1 for w in ws); acc = 0; tw = []
        for w in ws:
            tw.append(st + ln * acc / tot); acc += len(w) + 1
        tw.append(st + ln)
        i = 0
        for sent in [x for x in re.split(r"(?<=[.?!,])\s+", line) if x.strip()]:
            n = len(sent.split())
            for j in range(0, n, 3):
                a, b = i + j, min(i + j + 3, i + n)
                out.append((tw[a], tw[b], " ".join(ws[a:b])))
            i += n
    return out


def caption_pass(src, dst, lines, timing=None):
    f = lambda v: f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(v * 1000 % 1000):03d}"
    lines = list(lines)[:-1] if len(lines) > 1 else lines   # last line = end card voice; the card already shows it
    caps = timed_chunks(lines, timing) if timing else whisper_chunks(src, lines)
    if timing:   # self-review: each caption inside its own voice line, nothing on the end card, no overlaps
        wins = [(st + 0.1, st + 0.15 + ln + 0.05) for (st, ln), l in zip(timing, lines) if l and l.strip()]
        card = timing[len(lines)][0] if len(timing) > len(lines) else 1e9
        bad = [c for c in caps if not any(w0 <= c[0] and c[1] <= w1 for w0, w1 in wins) or c[1] > card]
        bad += [b for a, b in zip(caps, caps[1:]) if b[0] < a[1] - 0.01]
        if bad:
            raise RuntimeError(f"CHECK: captions out of sync ({len(bad)}): {bad[0]}")
    srt = "".join(f"{n}\n{f(a)} --> {f(max(b, a + 0.3))}\n{t}\n\n" for n, (a, b, t) in enumerate(caps, 1))
    sp = os.path.join(tempfile.mkdtemp(), "c.srt"); open(sp, "w", encoding="utf-8").write(srt)
    style = ("FontName=Archivo,FontSize=15,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
             "Outline=3,Shadow=0,MarginV=70,Alignment=2")
    esc = lambda p: p.replace("\\", "/").replace(":", "\\:")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"subtitles='{esc(sp)}':fontsdir='{esc(FONTS)}':force_style='{style}'",
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)


def polish(mp4, lines, segs=(), timing=None):
    """in place. Returns a short log line."""
    log = []
    total = dur(mp4); work = tempfile.mkdtemp(); cur = mp4
    try:
        a = os.path.join(work, "fx.mp4"); used = fx_pass(cur, a, total, segs); cur = a; log.append("fx ok: " + ",".join(used))
    except Exception as e:
        log.append("fx skipped: " + str(e)[:120])
    try:
        b = os.path.join(work, "cap.mp4"); caption_pass(cur, b, lines, timing); cur = b; log.append("captions ok")
    except Exception as e:
        log.append(("CHECK: " if "CHECK:" in str(e) else "") + "captions skipped: " + str(e)[:120])
    if cur != mp4 and dur(cur) > total * 0.9:
        shutil.copy(cur, mp4)
    return "polish: " + ", ".join(log)


if __name__ == "__main__":
    print(polish(sys.argv[1], sys.argv[2:]))
