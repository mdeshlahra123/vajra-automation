"""Claim guard (from 2026-10-24): never promise an exact number of uses. Allowed line:
"Ply se 2-3 guna zyada chalti hai, sahi handling ke saath." Also bans per-pour / yearly rupee maths built on a use count.
VARIETY GUARD (13 Nov 2026): blocks overused words (waterproof/paani/phool) if they appeared in last 3 reels."""
import re, json, os

SAFE_LINE = "Sahi handling ke saath ply se 2-3 guna zyada chalti hai."
SAFE_SHORT = "2-3 GUNA ZYADA"
BAD = re.compile(
    r"\b\d{1,3}\s*\+?\s*(?:[-–]|se|to)?\s*\d{0,3}\s*\+?\s*(?:baar|bar\b|times|uses?\b|pours?\b|dhalai|repeats?|reuse|cycles?|slab)"
    r"|(?:₹|rs\.?|rupees?)\s*\d{2,3}\b\s*(?:/|per|har|ek)?\s*(?:dhalai|pour)|har dhalai[^.\n]{0,20}(?:₹|rs)"
    r"|\d(?:\.\d)?\s*lakh\s*/?\s*(?:saal|year)|kharcha aadha|\d+\s*ply sheet ka kaam|1 vajra\s*=\s*\d",
    re.I)
OK = re.compile(r"2\s*[-–]\s*3\s*guna", re.I)
# 13 Nov: Hindi number words also count as a use number ("do baar use karke tut jata", "dus baar chala lo")
WORDNUM = re.compile(
    r"\b(?:do|teen|char|chaar|paanch|panch|chhe|saat|aath|nau|das|dus|bees|tees|chalis|chaalis|pachas|pachaas|sau|hazaar|"
    r"two|three|four|five|ten|twenty|forty|fifty|hundred|sainkdon)\s*(?:-|se|to)?\s*\w{0,8}\s*"
    r"(?:baar|bar|times|uses?|pours?|dhalai|repeats?|cycles?)\b", re.I)

# Words that get overused (owner complaint 13 Nov 2026): paani paani paani every reel
OVERUSED_WORDS = [
    (r"\bwaterproof\b", "waterproof", 3),
    (r"\bpaani\b", "paani", 3),
    (r"\bphool(?:ti|ta|e|i)?\b", "phool", 3),
    (r"\bbarish\b", "barish", 3),
    (r"\bkeechad\b", "keechad", 3),
]
OVERUSED = [(re.compile(pat, re.I), word, limit) for pat, word, limit in OVERUSED_WORDS]


def bad(text):
    """True if the text promises a use count or use-count money maths."""
    t = OK.sub("", text or "")
    return bool(text) and bool(BAD.search(t) or WORDNUM.search(t))


def _recent_captions(n=3):
    """Last n posted reel captions (to check for overused words)."""
    try:
        q = json.load(open(os.path.join(os.path.dirname(__file__), "..", "queue.json"), encoding="utf-8"))
        posted = [p for p in q.get("posts", []) if p.get("posted") and p.get("video")][-n:]
        caps = []
        for p in posted:
            try:
                caps.append(open(os.path.join(os.path.dirname(__file__), "..", p["caption"]), encoding="utf-8").read())
            except:
                pass
        return "\n".join(caps)
    except:
        return ""


def overused(text):
    """True if text contains a word that appeared in the last 3 reels."""
    if not text:
        return False
    recent = _recent_captions(3)
    if not recent:
        return False
    for pattern, word, limit in OVERUSED:
        if pattern.search(text) and len(pattern.findall(recent)) >= limit:
            return True
    return False


def fix_line(text, short=False):
    if overused(text):
        return ""  # drop the line entirely if it's overused
    return (SAFE_SHORT if short else SAFE_LINE) if bad(text) else text


def fix_caption(text):
    """Replace every offending caption line with the safe line (once)."""
    out, used = [], False
    for line in (text or "").split("\n"):
        if bad(line):
            if not used:
                out.append(SAFE_LINE); used = True
        else:
            out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    for t in ["40+ baar chalta hai", "40-50 REPEATS", "40 se 50 pours chalegi", "Har dhalai sirf ₹88", "Saal ka 1.1 lakh / saal",
              "Ply se 2-3 guna zyada chalti hai", "Ek aadmi uthaye", "Har 5 slab pe naya ply?", "Kawardha site, 8x4 ft 12 mm",
              "Waterproof PP shuttering sheet", "Paani se nahi phoolti"]:
        print(f"bad={bad(t)} overused={overused(t)} | {t}")
