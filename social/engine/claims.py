"""Claim guard (from 2026-10-24): never promise an exact number of uses. Allowed line:
"Ply se 2-3 guna zyada chalti hai, sahi handling ke saath." Also bans per-pour / yearly rupee maths built on a use count."""
import re

SAFE_LINE = "Sahi handling ke saath ply se 2-3 guna zyada chalti hai."
SAFE_SHORT = "2-3 GUNA ZYADA"
BAD = re.compile(
    r"\b\d{1,3}\s*\+?\s*(?:[-–]|se|to)?\s*\d{0,3}\s*\+?\s*(?:baar|bar\b|times|uses?\b|pours?\b|dhalai|repeats?|reuse|cycles?|slab)"
    r"|(?:₹|rs\.?|rupees?)\s*\d{2,3}\b\s*(?:/|per|har|ek)?\s*(?:dhalai|pour)|har dhalai[^.\n]{0,20}(?:₹|rs)"
    r"|\d(?:\.\d)?\s*lakh\s*/?\s*(?:saal|year)|kharcha aadha|\d+\s*ply sheet ka kaam|1 vajra\s*=\s*\d",
    re.I)
OK = re.compile(r"2\s*[-–]\s*3\s*guna", re.I)


def bad(text):
    """True if the text promises a use count or use-count money maths."""
    return bool(text) and bool(BAD.search(OK.sub("", text)))


def fix_line(text, short=False):
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
              "Ply se 2-3 guna zyada chalti hai", "Ek aadmi uthaye", "Har 5 slab pe naya ply?", "Kawardha site, 8x4 ft 12 mm"]:
        print(bad(t), "|", t)
