"""Caption cleanup (ideas from github.com/Jakeschincariol/instagram-agent-skill, ig-caption + ig-human):
- Hashtags: our full set of 11, as before (owner, 29 Oct). daily-post.ps1 ignores hashtags when it checks the live caption, so a post is never deleted if Instagram trims them.
- Search reads caption words -> make sure "PP shuttering sheet" + area words are in the text.
- Strip invisible characters and em/en dashes, curly quotes.
Usage: python caption_fix.py <file...>   or imported: fix(text)"""
import re, sys

TAGS = "#PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai"
SEARCH = "PP shuttering sheet, plastic shuttering. Raipur, Durg, Bhilai aur poore India mein delivery."
INVIS = re.compile("[\u200b-\u200f\u2060-\u2064\ufeff\u00ad\u202a-\u202e\U000e0000-\U000e007f]")


def fix(text):
    t = INVIS.sub("", text).replace("\u00a0", " ").replace("\u202f", " ")
    t = t.replace("\u2014", ",").replace("\u2013", "-").replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2026", "...")
    lines = [l for l in t.split("\n") if not re.fullmatch(r"\s*(#\w+\s*)+", l)]
    body = "\n".join(lines).rstrip()
    body = re.sub(r"(?<!\S)#\w+", "", body)            # no tags inside the text either
    if "shuttering sheet" not in body.lower():
        body += "\n\n" + SEARCH
    return re.sub(r"\n{3,}", "\n\n", body).strip() + "\n\n" + TAGS


if __name__ == "__main__":
    for f in sys.argv[1:]:
        s = open(f, encoding="utf-8").read(); n = fix(s)
        if n != s:
            open(f, "w", encoding="utf-8").write(n); print("fixed", f)
