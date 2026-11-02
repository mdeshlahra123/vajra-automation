"""Hypit pilot: make the voiceover lines (Gemini TTS, same voice as our reels) as separate WAVs.
Writes assets/hypit-pilot/vo-<n>.wav + lines.json. Env: GEMINI_API_KEY."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"))
from make_reel import tts, A
LINES = [
    ("hook", "Har slab pe naya ply? Phir wahi kharcha."),
    ("pain", "Paani lagte hi ply phool jaati hai, aur thekedar ka tension badhta hai."),
    ("answer", "Iska solution hai VAJRA PP shuttering sheet."),
    ("benefit", "Waterproof, halki, aur sahi handling ke saath ply se do teen guna zyada chalti hai."),
    ("cta", "Comment mein PP likhiye, rate aapke DM mein."),
]
out = A("assets", "hypit-pilot"); os.makedirs(out, exist_ok=True)
meta = []
for n, (key, line) in enumerate(LINES):
    p = os.path.join(out, f"vo-{key}.wav")
    d = tts(line, p)
    meta.append({"key": key, "line": line, "file": f"vo-{key}.wav", "secs": round(d, 2)})
    print(key, round(d, 2), line)
json.dump(meta, open(os.path.join(out, "lines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
