"""A2 planner (GitHub): keeps the reel queue full with Muse-generated VAJRA reels.

When pending reels + reels still being generated < TARGET, it writes ONE new batch into social/gen-jobs.json:
a 3-clip mini story (problem with brown ply -> turn -> VAJRA answer), each clip a Muse video prompt (10 s, 9:16,
spoken Hinglish line) that starts from a REAL VAJRA photo, so the sheet always looks like our sheet.
The Oracle server worker (social/server/vajra_gen.py) generates the clips; gen_build.py builds the reel.
  python social/engine/gen_plan.py          plan if needed
  python social/engine/gen_plan.py --force  plan one batch now
  python social/engine/gen_plan.py --show   print the plan, write nothing
"""
import datetime, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
JOBS = os.path.join(ROOT, "social", "gen-jobs.json")
QUEUE = os.path.join(ROOT, "social", "queue.json")
TARGET, MAX_PER_DAY = 4, 3        # reels waiting; batches started per day (3 clips each -> 9 of Muse's 15 daily videos)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# start frames: real photos. Problem clips start from brown ply; answer clips from real VAJRA sheets / results.
PROBLEM = {"ply-pile": "a pile of old broken brown plywood boards at an Indian site"}
ANSWER = {
    "godown": "stacks of new plain light-grey VAJRA sheets on pallets in a warehouse",
    "warehouse": "large ready stock of plain grey VAJRA sheets in a warehouse",
    "slab-underside": "a slab underside fully shuttered with plain grey VAJRA sheets on a yellow steel frame",
    "column-smooth2": "a smooth finished concrete column on site",
    "beam-box": "plain grey VAJRA sheets inside a red steel beam frame on site",
    "sheet-cut": "a hand cutting a plain grey VAJRA sheet with a normal circular cutter",
    "p2-column": "a tall column shuttered with plain grey VAJRA panels on a rooftop site",
    "finish-column": "a finished concrete column just after VAJRA shuttering was removed",
    "v5-cage": "a column steel cage with plain grey VAJRA panels being placed",
}
REF_PATH = {**{k: f"assets/photos/{k}.jpg" for k in list(PROBLEM) + list(ANSWER)},
            "godown": "assets/refs/godown.jpg"}

PROMPT = """You write a 3-clip Instagram reel for VAJRA (plain light-grey hollow PP plastic shuttering sheets, Chhattisgarh, India).
Each clip is one 10-second realistic phone video made by an AI video model that STARTS from a real photo (described below)
and continues it. Story: clip 1 = the problem with old brown plywood (hook in the first 2 seconds), clip 2 = the turn,
clip 3 = the VAJRA answer. Angle for today: {angle}
Start photos: clip 1: {p1}. clip 2: {p2}. clip 3: {p3}.
For every clip write:
- "action": what happens, continuing naturally from that photo (1-2 sentences; Indian workers/contractor; real site feel).
- "line": ONE short spoken line in Hinglish (Latin letters), max 9 words, said by a person in the clip.
Rules (any break = rejected):
- Brown plywood only in problem moments; the VAJRA sheet is plain light grey with NO text or logo.
- Never a number of uses/times, never a price, never how fast ply breaks (no "ek baar mein tut gaya"). Allowed only:
  "sahi handling ke saath ply se 2-3 guna zyada chalti hai".
- No words: waterproof, paani, barish, rain, phool (water angle is resting). No brand name in speech except VAJRA.
- No unsafe work, no children, no famous people.
Also write "hook": the caption's first line (Hinglish, max 9 words) and "title": short internal title.
JSON only: {{"title":"","hook":"","clips":[{{"action":"","line":""}},{{"action":"","line":""}},{{"action":"","line":""}}]}}"""

BANNED = re.compile(r"waterproof|paani|pani\b|barish|baarish|\brain\b|phool|keechad|₹|\brs\.?\s*\d|rupe", re.I)


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def problems(t):
    import claims
    out = []
    if claims.bad(t): out.append("use-count")
    if BANNED.search(t or ""): out.append("banned word")
    return out


def muse_prompt(photo_desc, action, line):
    return (f"Realistic vertical 9:16 phone video, 10 seconds, natural light, steady handheld camera. Start exactly from this photo "
            f"({photo_desc}) and continue it: {action} A person in the clip says \"{line}\" in clear Hindi. "
            "Any shuttering sheet that is grey must stay plain light grey with no text, letters or logo. "
            "Plywood is brown wood. No subtitles, no on-screen text, no watermarks.")


def need():
    q = load(QUEUE, {"posts": []}); jb = load(JOBS, {"jobs": [], "batches": {}})
    pend = sum(1 for p in q["posts"] if p.get("video") and not p.get("posted"))
    gen = sum(1 for b in jb["batches"].values() if b.get("status") == "waiting")
    today = datetime.datetime.now(IST).date().isoformat()
    started = sum(1 for b in jb["batches"].values() if b.get("created", "").startswith(today))
    print(f"pending reels {pend}, generating {gen}, started today {started}")
    return pend + gen < TARGET and started < MAX_PER_DAY


def llm(prompt):
    """Free stack first: OmniRoute on the server (combo claude-free, falls through NVIDIA/OpenRouter/LLM7/Groq/Gemini...);
    Gemini via gem.py only if OmniRoute is not reachable (e.g. on GitHub)."""
    import urllib.request
    key = os.environ.get("OMNIROUTE_KEY") or next((open(p).read().strip() for p in
          (os.path.expanduser("~/.omniroute-vajra.key"), r"C:\Users\mehul\.omniroute-laptop\key.txt") if os.path.exists(p)), "")
    if key:
        try:
            req = urllib.request.Request(os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128") + "/v1/chat/completions",
                data=json.dumps({"model": "claude-free", "temperature": 0.8, "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            txt = json.load(urllib.request.urlopen(req, timeout=180))["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0)) if m else {}
        except Exception as e:
            print("omniroute failed, trying gemini:", str(e)[:120])
    import gem
    r = gem.text("gemini-3.5-flash-lite", prompt, json_mode=True)
    return r[0] if isinstance(r, list) and r and isinstance(r[0], dict) else r


def plan():
    g = load(os.path.join(ROOT, "social", "growth-plan.json"), {})
    angles = [a for a in g.get("next_angles", []) if not BANNED.search(a)] or ["one man can lift a VAJRA sheet", "smooth concrete finish", "easy cutting"]
    jb = load(JOBS, {"jobs": [], "batches": {}})
    recent = [b.get("photos", [None, None, None])[2] for b in list(jb["batches"].values())[-6:]]
    answers = [k for k in ANSWER if k not in recent] or list(ANSWER)
    p3 = random.choice(answers); p2 = random.choice([k for k in ANSWER if k != p3])
    photos = ["ply-pile", p2, p3]
    angle = random.choice(angles[:3])
    extra = ""
    for _ in range(3):
        try:
            r = llm(PROMPT.format(angle=angle, p1=PROBLEM["ply-pile"], p2=ANSWER[p2], p3=ANSWER[p3]) + extra) or {}
        except Exception as e:
            print("planner model failed:", str(e)[:120]); r = {}
        clips = [c for c in r.get("clips", []) if c.get("action") and c.get("line")][:3]
        txt = json.dumps(r, ensure_ascii=False)
        bad = problems(txt)
        if len(clips) == 3 and not bad and r.get("hook"):
            return {"title": r.get("title", angle)[:70], "hook": r["hook"][:90], "angle": angle, "photos": photos, "clips": clips}
        extra = f"\n\nYour last answer broke the rules ({', '.join(bad) or 'need exactly 3 clips + hook'}). Rewrite."
    return None


def main():
    if "--force" not in sys.argv and "--show" not in sys.argv and not need():
        print("queue is full enough; nothing planned"); return
    p = plan()
    if not p:
        sys.exit("no plan passed the rules")
    now = datetime.datetime.now(IST); bid = "gen-" + now.strftime("%m%d-%H%M")
    descs = [PROBLEM.get(k) or ANSWER[k] for k in p["photos"]]
    jobs = [{"id": f"{bid}-{i + 1}", "batch": bid, "kind": "video", "size": "9:16", "start_image": REF_PATH[p["photos"][i]],
             "prompt": muse_prompt(descs[i], c["action"], c["line"]), "line": c["line"], "status": "todo", "tries": 0,
             "out": f"assets/clips/gen/{bid}-{i + 1}.mp4"} for i, c in enumerate(p["clips"])]
    if "--show" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8"); print(json.dumps({"batch": p, "jobs": jobs}, ensure_ascii=False, indent=1)); return
    jb = load(JOBS, {"jobs": [], "batches": {}})
    jb["jobs"] += jobs
    jb["batches"][bid] = {"status": "waiting", "created": now.isoformat(timespec="minutes"), "title": p["title"], "hook": p["hook"],
                          "angle": p["angle"], "photos": p["photos"], "lines": [c["line"] for c in p["clips"]]}
    json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PLANNED", bid, "|", p["hook"])


if __name__ == "__main__":
    main()
