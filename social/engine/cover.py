"""Reel cover in the VAJRA grid style (beige card, big hook, real frame, logo + phone).
Grid shows the centre 3:4 (y 240-1680 of 1920), so everything important sits there.
Usage: python cover.py <video> "<hook line 1|line 2>" <out.jpg> [seconds]"""
import os, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT = os.path.join(ROOT, "assets", "brand", "Archivo.ttf").replace("\\", "/").replace(":", "\\:")
LOGO = os.path.join(ROOT, "assets", "brand", "logo-onlight.png")
FF = os.environ.get("FFMPEG", "ffmpeg")
INK, PAPER, GOLD = "0x221D18", "0xE7E2D8", "0xA87A3F"


def make(video, hook, out, at=None):
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
    if at is None:
        dur = float(subprocess.run([FF, "-i", video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")[-1])
        at = min(2.5, dur / 3)
    fc = (f"color=c={PAPER}:s=1080x1920[bg];[0:v]crop=iw:ih*0.62:0:ih*0.30,scale=936:{ph}:force_original_aspect_ratio=increase,crop=936:{ph}[ph];"
          f"[1:v]scale=300:-1[lg];[bg][ph]overlay=72:{top}[a];[a]{txt},drawbox=x=72:y=1525:w=936:h=4:color={GOLD}:t=fill[b];"
          f"[b][lg]overlay=72:1560,drawtext=fontfile='{FONT}':text='83050 70160':fontsize=56:fontcolor={INK}:x=1008-text_w:y=1565,"
          f"drawtext=fontfile='{FONT}':text='Call / WhatsApp':fontsize=30:fontcolor={GOLD}:x=1008-text_w:y=1630[v]")
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(at), "-i", video, "-i", LOGO, "-filter_complex", fc,
                    "-map", "[v]", "-frames:v", "1", "-q:v", "2", out], check=True)
    return out


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else None)
