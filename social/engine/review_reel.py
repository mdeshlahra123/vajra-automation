"""Delivery reviewer: compares the FINISHED reel against the approved script before it goes to Telegram.
For every scene it takes 2 frames from the final mp4 and asks Gemini: does what we SEE match what the script
PROMISED (type ai/photo/clip, subject, words on screen, voiceover)? Also checks brand rules.
Returns {"ok": bool, "scenes": [{"n", "match", "seen", "problem"}], "issues": [...]}.

  review(final_mp4, scenes, work)   scenes = [{"start", "end", "promised", "vo", "text"}]
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem
from make_reel import sh, TEXT_MODEL

RULES = ("Brand rules: problem/ply scenes must show BROWN wooden plywood, never the grey VAJRA sheet. VAJRA scenes show a "
         "plain light-grey hollow PP sheet with no printing. No visible price, no competitor logo, no readable text or logos on "
         "any sheet, no deformed hands/faces, no glitches. AI scenes are allowed anywhere, including the VAJRA sheet in use or a demo.")


def review(final, scenes, work):
    parts, idx = [], []
    for n, s in enumerate(scenes):
        for k, t in enumerate((s["start"] + (s["end"] - s["start"]) * 0.3, s["start"] + (s["end"] - s["start"]) * 0.75)):
            f = os.path.join(work, f"rv{n}_{k}.jpg")
            sh("ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", final, "-frames:v", "1", "-vf", "scale=-2:640", f)
            parts.append(gem.img_part(f)); idx.append(n)
    script = "\n".join(f"Scene {n + 1} ({s['start']:.1f}-{s['end']:.1f}s): PROMISED: {s['promised']} | on-screen text: {s.get('text', '')} | voice: {s.get('vo', '')}"
                       for n, s in enumerate(scenes))
    q = (f"You are the final reviewer of an Instagram reel before the owner sees it. The approved script:\n{script}\n\n{RULES}\n\n"
         f"The images are 2 frames per scene in order (scene numbers: {idx}). For each scene say what you actually see and "
         "whether it matches what was promised (an AI video scene must be moving video of the promised subject; a still photo "
         "of a godown when a ply problem was promised is NOT a match). ok=false if any scene does not match or breaks a rule.\n"
         'JSON only: {"ok": true/false, "scenes": [{"n": 1, "match": true/false, "seen": "...", "problem": ""}], "issues": ["..."]}')
    r = gem.interact(TEXT_MODEL, [{"type": "text", "text": q}] + parts, response_format={"type": "text", "mime_type": "application/json"})
    j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
    j["ok"] = bool(j.get("ok")) and all(s.get("match", False) for s in j.get("scenes", []))
    return j


def summary(j, log_notes=()):
    """Short Hinglish line for the Telegram approval card."""
    notes = [n for n in log_notes if n]
    if j.get("ok") and not notes:
        return "✅ Reviewer: script aur video match karte hain."
    bad = [f"Scene {s.get('n')}: {s.get('problem') or s.get('seen')}" for s in j.get("scenes", []) if not s.get("match")]
    return ("⚠️ Reviewer: script se alag hai, dhyan se dekho.\n" + "\n".join((notes + bad + j.get("issues", []))[:5]))[:450]
