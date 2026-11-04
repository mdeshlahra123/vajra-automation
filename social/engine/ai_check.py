"""Is this clip/photo AI-generated (Google Flow etc.) or real footage? Owner (4 Nov): no captions, detect it.
Gemini free key looks at 3 frames (video) or the image. Unsure or error -> AI (safer: the post then gets the AI label).
  ai, desc = ai_check.check(path)
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

Q = ("Look at these frame(s) from one clip/photo sent by the owners of VAJRA (grey PP hollow shuttering sheets, India). "
     "Decide if it is AI-generated (Google Flow / Veo / Gemini image: too-perfect light, waxy faces, odd hands, melting details, "
     "smooth fake motion, impossible text) or REAL phone footage of a real site. JSON only: "
     '{"ai": true/false, "sure": true/false, "desc": "one line: what it shows (brown ply / grey VAJRA sheet / column / slab / labour / contractor ...)"}')


def frames(path, work):
    try:
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                 capture_output=True, text=True).stdout.strip() or 6)
    except Exception:
        d = 6
    out = []
    for i, t in enumerate((d * 0.15, d * 0.5, d * 0.85)):
        f = os.path.join(work, f"f{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=-2:640", f])
        if os.path.exists(f):
            out.append(f)
    return out


def check(path):
    import gem
    try:
        work = tempfile.mkdtemp()
        imgs = [path] if path.lower().endswith((".jpg", ".jpeg", ".png")) else frames(path, work)
        r = gem.interact("gemini-3.5-flash-lite", [{"type": "text", "text": Q}] + [gem.img_part(x) for x in imgs],
                         response_format={"type": "text", "mime_type": "application/json"})
        j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
        ai = bool(j.get("ai")) or not j.get("sure", True)
        return ai, (j.get("desc") or "")[:160]
    except Exception as e:
        print("ai_check failed, marking AI:", str(e)[:120])
        return True, ""


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, check(p))
