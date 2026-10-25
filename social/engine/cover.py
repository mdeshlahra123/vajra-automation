"""Reel cover in the VAJRA grid style (beige card, big hook, real frame, logo + phone).
Grid shows the centre 3:4 (y 240-1680 of 1920), so everything important sits there.
Usage: python cover.py <video> "<hook line 1|line 2>" <out.jpg> [seconds]"""
import os, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT = os.path.join(ROOT, "assets", "brand", "Archivo.ttf").replace("\\", "/").replace(":", "\\:")
LOGO = os.path.join(ROOT, "assets", "brand", "logo-onlight.png")
FF = os.environ.get("FFMPEG", "ffmpeg")
INK, PAPER, GOLD = "0x221D18", "0xE7E2D8", "0xA87A3F"


def make(video, hook, out, at=None, y0=0.30, y1=0.92):
    d = tempfile.mkdtemp()
    lines = [l.strip() for l in hook.replace("\n", "|").split("|") if l.strip()][:3]
    files = []
    for i, l in enumerate(lines):
        p = os.path.join(d, f"l{i}.txt"); open(p, "w", encoding="utf-8").write(l); files.append(p.replace("\\", "/").replace(":", "\\:"))
    size = 118 if max(len(l) for l in lines) <= 14 else 96 if max(len(l) for l in lines) <= 18 else 80
    txt = ",".join(f"drawtext=fontfile='{FONT}':textfile='{f}':fontsize={size}:fontcolor={INK}:x=72:y={300 + i * int(size * 1.02)}"
                   for i, f in enumerate(files))
    top = 300 + len(lines) * int(size * 1.02) + 40          # photo starts under the text
    ph = 1500 - top                                         # photo ends at 1500, footer 1520-1660
    img = video.lower().endswith((".jpg", ".png"))
    if at is None and not img:
        dur = float(subprocess.run([FF, "-i", video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")[-1])
        at = min(2.5, dur / 3)
    fc = (f"color=c={PAPER}:s=1080x1920:d=1[bg];[0:v]setpts=PTS-STARTPTS,{"" if img else f"crop=iw:ih*{y1 - y0}:0:ih*{y0},"}scale=936:{ph}:force_original_aspect_ratio=increase,crop=936:{ph}[ph];"
          f"[1:v]scale=300:-1[lg];[bg][ph]overlay=72:{top}[a];[a]{txt},drawbox=x=72:y=1525:w=936:h=4:color={GOLD}:t=fill[b];"
          f"[b][lg]overlay=72:1560,drawtext=fontfile='{FONT}':text='83050 70160':fontsize=56:fontcolor={INK}:x=1008-text_w:y=1565,"
          f"drawtext=fontfile='{FONT}':text='Call / WhatsApp':fontsize=30:fontcolor={GOLD}:x=1008-text_w:y=1630[v]")
    subprocess.run([FF, "-v", "error", "-y"] + ([] if img else ["-ss", str(at)]) + ["-i", video, "-i", LOGO] + ["-filter_complex", fc,
                    "-map", "[v]", "-frames:v", "1", "-q:v", "2", out], check=True)
    return out


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else None)


def smart(video, caption, out, model="gemini-3.8-flash"):
    """Gemini picks the best of 8 frames + writes a 2-line hook; falls back to a text-only card. Returns a short note."""
    import json, re
    sys.path.insert(0, os.path.dirname(__file__)); import gem
    d = tempfile.mkdtemp()
    s = subprocess.run([FF, "-i", video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    du = max(1.0, float(s[1]) * 60 + float(s[2]) - 3.5)
    ts = [round(0.4 + i * (du - 0.4) / 7, 2) for i in range(8)]
    inp = [{"type": "text", "text": (
        "These are 8 frames (0-7) of a VAJRA PP shuttering sheet reel. Caption:\n" + caption[:600] +
        "\n\nPick the frame for an Instagram grid cover: sharp, well lit, clearly shows what the hook says (real site, sheet, people), "
        "no big burned-in caption in the middle part, no end card. Write a hook of 2 short lines (each <=16 characters, Hinglish, sentence case, "
        "no numbers of uses, no price). Also give the vertical band of the frame to keep (y0,y1 as fractions of height, band >=0.45 tall) "
        "that avoids burned-in text. If no frame is good, frame=-1. JSON only: "
        '{"frame": 0-7 or -1, "line1": "...", "line2": "...", "y0": 0.25, "y1": 1.0, "why": "short"}')}]
    for i, t in enumerate(ts):
        p = os.path.join(d, f"{i}.jpg")
        subprocess.run([FF, "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf", "scale=360:-2", p], check=True)
        inp += [{"type": "text", "text": f"Frame {i}:"}, gem.img_part(p)]
    r = gem.interact(model, inp, response_format={"type": "text", "mime_type": "application/json"})
    j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
    hook = (j.get("line1", "").strip() + "|" + j.get("line2", "").strip()).strip("|") or "VAJRA PP|panel."
    import claims
    if claims.bad(hook): hook = "Ply se 2-3 guna|zyada chale."
    f = int(j.get("frame", -1))
    if 0 <= f < 8:
        y0 = min(max(float(j.get("y0", .25)), 0), .55); y1 = max(min(float(j.get("y1", 1)), 1), y0 + .45)
        make(video, hook, out, at=ts[f], y0=y0, y1=y1)
    else:
        text_card(hook, out)
    return f"frame {f}: {hook.replace('|', ' / ')} ({j.get('why', '')})"


def text_card(hook, out, sub="VAJRA PP panel"):
    d = tempfile.mkdtemp(); fs = []
    for i, l in enumerate(hook.split("|")[:3]):
        p = os.path.join(d, f"t{i}.txt"); open(p, "w", encoding="utf-8").write(l); fs.append(p.replace("\\", "/").replace(":", "\\:"))
    sp = os.path.join(d, "s.txt"); open(sp, "w", encoding="utf-8").write(sub); sp = sp.replace("\\", "/").replace(":", "\\:")
    txt = ",".join(f"drawtext=fontfile='{FONT}':textfile='{f}':fontsize=150:fontcolor={INK}:x=72:y={520 + i * 158}" for i, f in enumerate(fs))
    fc = (f"color=c={PAPER}:s=1080x1920:d=1[bg];[1:v]scale=300:-1[lg];[bg]{txt},drawtext=fontfile='{FONT}':textfile='{sp}':fontsize=54:fontcolor={GOLD}:x=72:y={560 + len(fs) * 158}"
          f",drawbox=x=72:y=1525:w=936:h=4:color={GOLD}:t=fill[b];[b][lg]overlay=72:1560,drawtext=fontfile='{FONT}':text='83050 70160':fontsize=56:fontcolor={INK}:x=1008-text_w:y=1565,"
          f"drawtext=fontfile='{FONT}':text='Call / WhatsApp':fontsize=30:fontcolor={GOLD}:x=1008-text_w:y=1630[v]")
    subprocess.run([FF, "-v", "error", "-y", "-i", LOGO, "-filter_complex", fc.replace("[1:v]", "[0:v]"), "-map", "[v]", "-frames:v", "1", "-q:v", "2", out], check=True)
