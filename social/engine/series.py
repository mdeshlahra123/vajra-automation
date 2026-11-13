"""'Shuttering Ki Duniya': daily 3D cartoon series (owner, 13 Nov; KaarigarX-style talking objects).
Every day: 3 episodes, each = one header message + one copy-ready Google Flow prompt per 8-second part.
Character looks are FIXED text below and pasted into every prompt, so the characters look the same every time.
Episode code S<n>: the owner sends an episode's clips together, in order, with "S<n>" in a caption;
series_match.py then builds the reel (parts + voiced end card) and sends it for approval.
  python social/engine/series.py           write + send today's 3 episodes
  python social/engine/series.py --show    print only
Env: GEMINI_FREE_KEY / GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
STATE = os.path.join(ROOT, "social", "series-state.json")
MODEL = "gemini-3.5-flash-lite"
PER_DAY = 3

STYLE = ("Single continuous 8-second shot, vertical 9:16, high-quality 3D animated cartoon (Pixar-like), "
         "expressive faces with big eyes and moving mouths, warm golden light, half-built Indian house construction site background, "
         "lip-synced Hindi dialogue. No text, no letters, no logos, no subtitles, no character name tags, no title cards anywhere in the frame. No humans: only the listed talking objects.")
CHARS = {
    "ply": "PLY BHAIYA: an old brown wooden plywood board with a tired grumpy face, swollen chipped edges, a few cracks, a small bandage on one corner; deep tired voice.",
    "vajra": "VAJRA SHEET: a tall rectangular light-grey hollow plastic shuttering sheet (thin edge shows small hollow channels), standing upright, calm confident smiling face, two thin grey arms, friendly clear voice; completely plain surface with NO words, letters or logo on it.",
    "balli": "BALLI: a tall thin bamboo prop pole with a skinny face and a nervous shaky voice.",
    "sariya": "SARIYA USTAD: a wise old steel rebar bar with a grey moustache and round spectacles, ribbed texture, deep calm teacher voice.",
    "chhotu": "CHHOTU: a tiny round grey concrete cover block, cheerful child voice, often ignored.",
    "mami": "CONCRETE MAMI: a big friendly blob of wet grey concrete with a loud aunty voice and a bindi.",
}
# knowledge topics only a shuttering company can teach. Water/rain topics wait (water angle resting since 13 Nov).
TOPICS = [
    "Shuttering jaldi kholne ki galti: concrete ko set hone ka time chahiye (exact din engineer bataye)",
    "Honeycombing: column mein chhed kyun aate hain (vibration kam, gap se slurry bah gayi)",
    "Cover block kyun zaroori hai: sariya ke neeche gap nahi to jung",
    "Balli ki doori: props door door lage to slab latak jaata hai (spacing engineer se confirm)",
    "Shuttering oil / release agent: kyun lagate hain, kam ya zyada lagane ka nuksan",
    "Column bulge: shuttering ki bracing kamzor to column pet nikal leta hai",
    "Slab ke beech props hilane ki galti: dhalai ke baad props jaldi mat hatao",
    "Joint se slurry leak: shuttering ke joints tight na ho to cement paani bah jaata hai",
    "Beam ka bottom ulta: shuttering level na ho to beam tedhi",
    "Ply ka bhaari wazan: do log chahiye, VAJRA sheet ek aadmi utha leta hai",
    "Ply ki keelein aur chhed: har baar keel thokne se ply ki zindagi kam",
    "De-shuttering mein ply todna: hathode se maarna galat, sahi tarika",
    "Shuttering ke baad concrete surface: rough vs smooth finish, plaster ka kharcha",
    "Staircase shuttering ki galtiyan: step ki height barabar na ho",
    "Sariya ka overlap: chhota overlap kamzor (length engineer se confirm)",
    "Concrete mein zyada paani milana: kaam aasan, mazbooti kam",
    "Vibrator kitna chalana: kam to honeycomb, zyada to segregation",
    "Shuttering ke andar kachra: dhalai se pehle saaf karo",
    "Chhajja / sunshade shuttering: support kam to chhajja jhuk jaata hai",
    "Lintel shuttering: khidki ke upar beam ka dhyan",
    "Purani ply ka dobara istemal: phooli hui ply se tedha slab",
    "Cutting: ply ki cutting mein waste, VAJRA sheet normal cutter se kat-ti hai",
    "Shuttering stock ki dekhbhaal: dhoop aur zameen se bachakar rakhna",
    "Contractor ki chinta: shuttering ka kharcha har project mein (no price, no use-count)",
    "Site safety: shuttering pe chadhte waqt balli hilna",
    "Column ki seedhai: plumb check kyun zaroori",
    "Slab ki motai barabar: level pin aur shuttering level",
    "Retaining / wall shuttering: tie rod aur spacer",
]
CODE = re.compile(r"^S\d+$")

GEN = """You write ONE episode of "Shuttering Ki Duniya", a Hindi 3D-cartoon Instagram series for VAJRA (grey PP shuttering sheets,
Chhattisgarh). Like KaarigarX "Talking Tools": construction objects with faces talk and teach one useful, correct lesson.
Topic: {topic}
Characters (use 2-4, by id): {chars}
Write exactly {n} parts of 8 seconds each (total about {secs} s, must fit one 30-second video). Part 1 = the hook in the first 2 seconds
(a mistake, shock or question). Part 2 = why it goes wrong. Part 3 = the right way + "Follow karo Shuttering Ki Duniya ke liye". VAJRA Sheet appears only if natural (not every episode sells).
Rules (any break = rejected):
- Dialogue in simple spoken Hindi (Devanagari or Hinglish), max 2 short lines per part, max ~18 words per part.
- NEVER a number of uses/times (no "50 baar", "do baar use"), NEVER a price. Only allowed: "ply se 2-3 guna zyada chalti hai".
- Structural numbers (days, spacing, overlap, mm): say "engineer se confirm karein" instead of a number.
- No words: waterproof, paani se nahi phoolti, barish (water angle resting). No brand names except VAJRA in dialogue.
- "shot" = what we see and how the camera moves, 1-2 sentences, no dialogue in it.
Return JSON only: {{"title": "short Hinglish title", "hook": "caption first line", "parts": [{{"chars": ["ply","vajra"], "shot": "...", "dialogue": "PLY BHAIYA: '...' VAJRA SHEET: '...'"}}]}}"""

BANK = [{
    "title": "Shuttering jaldi kholi to kya hoga?", "hook": "Shuttering jaldi kholne ki galti 😱",
    "topic": TOPICS[0],
    "parts": [
        {"chars": ["balli", "ply", "mami"], "shot": "Balli trembles under a fresh slab, Ply Bhaiya pressed against its underside, Concrete Mami on top wobbles in shock.",
         "dialogue": "BALLI: 'Thekedar kal hi shuttering kholne wala hai!' CONCRETE MAMI: 'Kal? Main to abhi kachchi hoon!'"},
        {"chars": ["sariya", "ply", "mami"], "shot": "Sariya Ustad steps forward like a teacher and points at Concrete Mami; Ply Bhaiya nods, worried.",
         "dialogue": "SARIYA USTAD: 'Concrete ko set hone ka time chahiye. Kab kholna hai, engineer batata hai, andaze se nahi.'"},
        {"chars": ["vajra", "ply", "sariya"], "shot": "VAJRA Sheet slides off the slab smoothly while Ply Bhaiya cracks a little; everyone smiles at the camera.",
         "dialogue": "VAJRA SHEET: 'Sahi time pe, aaram se kholo.' SARIYA USTAD: 'Follow karo Shuttering Ki Duniya ke liye!'"},
    ]}]


def load():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"next_code": 1, "open": {}, "topics": {}}


def problems(text):
    import claims
    out = []
    if claims.bad(text): out.append("use-count")
    if re.search(r"₹|\brs\.?\s*\d|rupe|waterproof|barish|baarish", text or "", re.I): out.append("price/water word")
    return out


# 13 Nov (first live episode S1): every clip came out in a different place, with one character alone and the VAJRA sheet
# looking different each time, so the 5 clips did not feel like one story. Fix: ONE fixed set per episode, the whole cast in
# every part, parts 2+ say "continue the same scene", and the owner makes parts 2+ with Flow's Extend on the previous clip.
SETS = [
    "SET (keep identical in every shot): the ground floor of a half-built two-storey Indian brick house, a freshly cast concrete slab overhead held up by bamboo props, red brick walls, a steel ladder on the left, afternoon golden sunlight from the right, camera at waist height facing the back wall.",
    "SET (keep identical in every shot): an open rooftop of an Indian house under construction, rebar mesh laid for a slab, a row of grey and brown shuttering boards stacked on the right, a blue water drum on the left, soft morning light, camera at waist height facing the stack.",
    "SET (keep identical in every shot): a construction site yard in an Indian town, a concrete mixer in the back, a tall column box standing in the middle with bamboo supports, sand pile on the left, warm late-afternoon light, camera at waist height facing the column.",
]


def prompt_of(part, cast, setting, first):
    looks = " ".join(CHARS[c] for c in cast if c in CHARS)
    lead = ("Part 1 of a continuous scene." if first else
            "CONTINUE the exact same scene from the previous clip: same place, same camera spot, same light, same characters "
            "in the same places and looks. Nothing new appears.")
    return (f"{STYLE} {lead} {setting} Characters, all of them visible together in the frame the whole time: {looks} "
            f"Action: {part['shot'].strip()} Dialogue (Hindi): {part['dialogue'].strip()} "
            "Sound: only the dialogue, light construction site ambience, soft playful background music.")


def write(topic, n=3):   # owner 13 Nov: a Flow Extend video is max 30 s -> 3 parts x 8 s
    import gem
    extra = ""
    for _ in range(3):
        r = gem.text(MODEL, GEN.format(topic=topic, n=n, secs=n * 8, chars=", ".join(CHARS)) + extra, json_mode=True)
        if isinstance(r, list):   # model sometimes wraps the episode in a list
            r = r[0] if r and isinstance(r[0], dict) else {}
        parts = [p for p in r.get("parts", []) if p.get("shot") and p.get("dialogue")][:n]
        bad = [f"part {i + 1}: {problems(p['dialogue'] + ' ' + p['shot'])}" for i, p in enumerate(parts) if problems(p["dialogue"] + " " + p["shot"])]
        if len(parts) == n and not bad and r.get("title"):
            return {"title": r["title"].strip()[:70], "hook": (r.get("hook") or r["title"]).strip()[:90], "topic": topic, "parts": parts}
        extra = "\n\nYour last answer broke rules: " + "; ".join(bad or ["too few parts"]) + ". Rewrite."
    return None


def main():
    st = load(); d = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date().isoformat()
    used = st.setdefault("topics", {})
    rep = sys.argv[sys.argv.index("--replace") + 1] if "--replace" in sys.argv else None
    if rep:   # cancel a bad episode code and send one new episode instead
        old = st.get("open", {}).pop(rep, None) or {}
    # replace keeps the same topic (new prompts only) unless --new-topic
    topics = ([old["topic"]] if rep and old.get("topic") and "--new-topic" not in sys.argv
              else sorted(TOPICS, key=lambda t: used.get(t, "0000"))[:1 if rep else PER_DAY])
    eps = []
    for t in topics:
        ep = None
        try:
            ep = write(t)
        except Exception as e:
            print("write failed:", str(e)[:150])
        if not ep:
            # fallback only if its topic is not already covered today (13 Nov: bank episode repeated S1 as S3)
            ep = next((b for b in BANK if (b["topic"] == t if rep else used.get(b["topic"], "0000") < d) and all(b["topic"] != e["topic"] for e in eps)), None)
        if ep and not any(problems(p["dialogue"] + p["shot"]) for p in ep["parts"]):
            eps.append(ep)
    msgs = []
    for ep in eps:
        code = f"S{st['next_code']}"; st["next_code"] += 1
        cast = list(dict.fromkeys(c for p in ep["parts"] for c in p.get("chars", []) if c in CHARS))[:4]
        setting = SETS[st["next_code"] % len(SETS)]
        prompts = [prompt_of(p, cast, setting, i == 0) for i, p in enumerate(ep["parts"])]
        msgs.append((f"♻️ {rep} cancel. Uski jagah ye naya episode:\n" if rep else "") +
                    f"🎬 {code} · Shuttering Ki Duniya: {ep['title']}\n{len(prompts)} prompt neeche (har ek 8 sec).\n"
                    f"1) Prompt 1 se pehla clip banao.\n2) Baaki ke liye usi clip pe Flow ka EXTEND dabao aur agla prompt daalo "
                    f"(naya clip mat banao), taaki jagah aur characters same rahein.\n"
                    f"3) Poora video (max 30 sec) yahin bhejo, caption mein likho: {code}\nEnd card + awaaz main laga dunga.")
        msgs += prompts
        st["open"][code] = {"title": ep["title"], "hook": ep["hook"], "topic": ep["topic"], "n": len(prompts), "sent": d, "clips": [], "prompts": prompts}
        used[ep["topic"]] = d
    if not msgs:
        sys.exit("no episode passed the rules; nothing sent")
    if "--show" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8"); print("\n---\n".join(msgs)); return
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    for m in msgs:
        req = urllib.request.Request(api, data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": m[:4000]}).encode(),
                                     headers={"Content-Type": "application/json"})
        for k in range(4):   # Telegram sometimes resets the connection
            try:
                print(json.load(urllib.request.urlopen(req, timeout=30)).get("ok"), m[:50]); break
            except Exception as e:
                print("send retry", k + 1, str(e)[:80]); import time; time.sleep(3 + 3 * k)


if __name__ == "__main__":
    main()
