"""Daily Google Flow brief to the Telegram group: prompts only, no explanations.
Every prompt goes through a reviewer (Gemini) before sending: it checks brand rules and Flow/Veo prompt quality,
rewrites weak prompts into clear self-contained ones, and drops any it can't fix. Nothing unreviewed is sent.
One reel idea per day = 2 video shots (~40 of the 50 free daily credits). Results come back to the group with
caption "flow" -> make_real.py (AI label, problem-first edit, real VAJRA footage at the end).
  python social/flow_brief.py          review + send today's prompts
  python social/flow_brief.py --show   review + print only
Env: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, sys, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"))
import gem

MODEL = "gemini-3.5-flash-lite"  # free tier, fast (3.8-flash daily quota ran out and the run hit the timeout, 31 Oct)
# one idea = shots that belong to the same reel (problem part only; the answer is our real footage)
IDEAS = [
    # --- ply problem (brown plywood only; our real VAJRA footage is the answer) ---
    ["Brown plywood shuttering boards swollen and peeling after rain on an Indian site, water dripping",
     "Indian contractor shaking his head at wet damaged brown plywood boards in the rain"],
    ["Two Indian labourers struggling to carry one heavy brown plywood board across a site",
     "Tired Indian labourer sitting next to brown plywood boards, wiping sweat in the afternoon heat"],
    ["Slow move toward a pile of broken cracked brown plywood boards in the corner of a half-built Indian house",
     "Workers pulling brown plywood off a concrete slab underside, the board cracks and splinters"],
    # --- cost / labour worry (contractor story) ---
    ["Indian contractor at a site table looking at a bill book, holding his head in worry, brown plywood behind",
     "Small truck unloading new brown plywood boards at an Indian site, contractor watching the pile grow"],
    ["Close on an Indian contractor's tired face doing sums on a calculator at a dusty site table, evening light",
     "Hands flipping through a worn site expense notebook, brown plywood offcuts scattered nearby"],
    # --- general construction scenes (full-AI reel b-roll, no shuttering needed) ---
    ["Sunrise over a half-built two-storey Indian house with bamboo props and scaffolding",
     "Gloved hands tying steel rebar for a column at an Indian site in morning light"],
    ["Workers pouring and spreading wet concrete on a slab at an Indian site, seen from above",
     "Concrete mixer turning at an Indian site, a worker adding cement, dust in the air"],
    ["Wide drone-style rise over a busy Indian residential construction site, many workers, morning haze",
     "A mason smoothing fresh plaster on a brick wall with a trowel, close handheld shot"],
    # --- before / after storytelling (problem framing only) ---
    ["A rough uneven concrete column surface after formwork is removed on an Indian site, honeycomb patches visible",
     "An Indian engineer running a hand over a rough patchy concrete wall, frowning, site in background"],
    # --- added 3 Nov: more angles so the brief never repeats for weeks ---
    ["Monsoon rain pouring onto stacked brown plywood boards on an open Indian site, puddles forming around them",
     "Close shot of water dripping off the swollen edge of a brown plywood board, slow and detailed"],
    ["A worker hammering nails into a brown plywood board that splits along the edge, Indian site, afternoon light",
     "Bent rusty nails and splinters lying on a cracked brown plywood board on the ground, close handheld shot"],
    ["Indian site godown with a tall messy stack of old warped brown plywood boards, dim light from a doorway",
     "A worker pulling one warped brown plywood board out of a messy stack, it is curved and uneven"],
    ["Two Indian contractors arguing politely over a paper site register, brown plywood stacked behind them",
     "An Indian contractor on a phone call, looking stressed, walking past a pile of damaged brown plywood"],
    ["Early morning Indian construction site, labourers arriving with tiffin boxes, bamboo props and rebar in frame",
     "A tea break on an Indian site, labourers sitting on bricks drinking chai from small glasses, warm light"],
    ["Steel column cage standing tall on an Indian rooftop site against a clear blue sky, slow upward tilt",
     "Close slow move along a neatly tied rebar mesh on a slab before concrete, Indian site, golden light"],
    ["A wheelbarrow of fresh wet concrete being pushed up a wooden ramp on an Indian site, worker straining",
     "Concrete being poured into a column formwork from a bucket on an Indian site, splashing slightly"],
    ["Top-down drone-style view of a half-finished Indian house slab with workers spreading concrete in a pattern",
     "Time-of-day feel: sunset over a finished concrete slab on an Indian site, workers packing up tools"],
]

# --- 4 Nov: fresh prompts every day. Gemini writes new prompts from a rotating theme x camera-style mix and
# a list of recent prompts it must not repeat. AI may now show the VAJRA sheet too (owner, 4 Nov). IDEAS above = fallback.
THEMES = [
    "ply problem: swollen / peeling brown plywood after rain", "ply problem: heavy brown ply needs two labourers",
    "ply problem: brown ply cracks during de-shuttering", "contractor money worry over buying new ply again",
    "VAJRA answer: one labourer easily carrying a light plain grey hollow plastic shuttering sheet on his shoulder",
    "VAJRA answer: plain grey plastic shuttering sheets fixed as a column box, workers tightening clamps",
    "VAJRA answer: plain grey plastic sheets under a slab with bamboo props, concrete being poured on top",
    "VAJRA answer: worker washing a plain grey plastic shuttering sheet with a hose after de-shuttering, water running off",
    "VAJRA answer: freshly de-shuttered concrete column with a smooth clean finish, worker touching it",
    "VAJRA answer: neat stack of plain grey plastic shuttering sheets in a godown, morning light",
    "VAJRA answer: worker cutting a plain grey plastic shuttering sheet with a circular saw, clean edge",
    "before/after: rough honeycomb column vs smooth finished column", "monsoon site: rain on stacked boards",
    "site life: tea break, tiffin, labourers laughing", "site life: early morning arrival, tools, bamboo props",
    "construction b-roll: rebar tying, column cage, mesh before pour", "construction b-roll: concrete pour from above",
    "contractor skit moment: contractor surprised a single worker brings a sheet alone", "engineer inspecting a slab underside, nodding",
    "family moving into a newly built Indian house, finished concrete ceiling", "time feel: sunset over a finished slab",
    "macro texture: water beads on a plain grey plastic surface", "macro texture: wet concrete sliding off a smooth grey plastic surface",
    "truck unloading plain grey plastic shuttering sheets at a site, two workers stacking them quickly",
]
STYLES = ["slow push-in", "handheld walk-and-follow", "low angle looking up", "top-down drone-style", "static tripod wide",
          "close-up macro with shallow focus", "over-the-shoulder", "slow orbit around the subject", "whip pan reveal", "slow tilt up"]

GEN = """You write prompts for Google Flow (Veo video and Gemini image) for VAJRA, a PP shuttering sheet brand in Chhattisgarh, India.
Write {nv} VIDEO prompt(s) and {np} IMAGE prompt(s). Use these theme+style pairs, one per prompt, in order:
{pairs}
Rules:
- Video: one continuous 8-second shot, vertical 9:16, realistic handheld phone-video look, Indian site. Structure: camera, subject,
  action, setting, light, then "Sound:" with ambient sound only. Image: vertical 9:16 realistic photo, same detail but no Sound line.
- Plain simple English, 40-80 words each, self-contained, nothing the model could misread.
- Plywood is BROWN wood. Our VAJRA sheet = plain light-grey hollow plastic shuttering sheet, 12 mm, with NO printing, text or logo.
- No brand names, no text/signs/subtitles/watermarks, no dialogue, no famous faces, no children, nothing unsafe.
- Each prompt must feel different from the others AND from these recent prompts (different subject, place, light, time of day, camera):
{recent}
Return JSON only: {{"prompts":[{{"type":"video"|"image","prompt":"..."}}]}}"""


def similar(a, b):
    wa, wb = set(a.lower().split()), set(b.lower().split())
    return len(wa & wb) / max(1, len(wa | wb)) > 0.45


def generate(st, nv=2, np_=1):
    import random
    used = st.get("themes", {})
    themes = sorted(THEMES, key=lambda t: (used.get(t, ""), random.random()))[:nv + np_]
    pairs = "\n".join(f"{i + 1}. {'VIDEO' if i < nv else 'IMAGE'}: {t} | camera: {random.choice(STYLES)}" for i, t in enumerate(themes))
    recent = st.get("recent", [])[-40:]
    r = gem.text(MODEL, GEN.format(nv=nv, np=np_, pairs=pairs, recent="\n".join("- " + x[:140] for x in recent) or "- none"), json_mode=True)
    out = []
    for x in r.get("prompts", []):
        p = (x.get("prompt") or "").strip()
        if 30 <= len(p.split()) <= 110 and "vajra" not in p.lower() and not any(similar(p, q) for q in recent + [o[1] for o in out]):
            out.append(("📸" if x.get("type") == "image" else "🎬", p))
    return out, themes


REVIEW = """You review prompts for Google Flow (Veo 3.1 / Gemini Omni Flash video) for VAJRA, a PP shuttering sheet brand
in Chhattisgarh, India. The clips are the PROBLEM part of an Instagram reel; our real product footage is added later.

For each draft, return a final prompt that a non-technical person can paste into Flow as is. Requirements:
- One clear shot, 8 seconds, vertical 9:16, realistic handheld phone-video look on an Indian construction site.
- Structure: camera/shot, subject, action, setting, light, then a "Sound:" line with ambient sound only.
- Plain simple English, 40-80 words, no jargon, no lists, nothing the model could misread.
- IF the shot shows shuttering/formwork boards, they must be BROWN wooden plywood. Never a grey or plastic sheet
  (only when the draft is a ply-problem shot). General construction scenes (rebar, concrete pour, plaster,
  site views, a worried contractor) need no shuttering at all and are welcome.
- No brand names, no text, signs,
  logos, subtitles or watermarks in frame. No dialogue. People: ordinary Indian workers/contractors, no famous
  faces, no children, nothing unsafe or degrading.
- Must actually be makeable as a single continuous 8-second shot.
If a draft breaks a rule and cannot be fixed, set ok=false.
Return JSON only: {"prompts":[{"ok":true,"prompt":"...","problem":""}]} in the same order as the drafts.

Drafts:
"""


def review(drafts):
    r = gem.text(MODEL, REVIEW + "\n".join(f"{i + 1}. {d}" for i, d in enumerate(drafts)), json_mode=True)
    out = []
    for x in r.get("prompts", []):
        p = (x.get("prompt") or "").strip()
        bad = any(w in p.lower() for w in ("grey sheet", "gray sheet", "plastic sheet", "vajra", "text", "logo"))
        if x.get("ok") and 30 <= len(p.split()) <= 110 and not bad:
            out.append(p)
    return out


STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow-state.json")


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"sent": {}}


def pick(n, st):
    """n idea indexes, least recently sent first (never-sent first). Ties keep bank order."""
    last = st.get("sent", {})
    order = sorted(range(len(IDEAS)), key=lambda i: (last.get(str(i), "0000-00-00"), i))
    return order[:n]


def today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()


if __name__ == "__main__":
    d = today()
    st = load_state()
    if "--batch" in sys.argv:   # one-off varied batch: review N idea sets across the themes and send them together
        try:
            n = int(sys.argv[sys.argv.index("--batch") + 1])
        except (ValueError, IndexError):
            n = 4
        chosen = pick(max(1, n), st)
        head_fmt = "🎬 Flow prompts – {} alag-alag video (9:16). Jo achhe lage bana ke yahin bhejo"
    else:
        chosen = None
        head_fmt = "🎬 Flow " + d.strftime('%d %b') + " – {} prompt (9:16). Bana ke yahin bhejo, caption ki zarurat nahi."
    prompts, themes = [], []
    if chosen is None:
        try:
            gp, themes = generate(st)
            prompts = [f"{e} {p}" for e, p in gp]
        except Exception as e:
            print("generate failed, using bank:", str(e)[:150])
        if not prompts:
            chosen = pick(1, st)
    if chosen is not None:
        for i in chosen:
            prompts += review(IDEAS[i])
    head = head_fmt.format(len(prompts))
    if prompts and "--show" not in sys.argv:
        for i in chosen or []:
            st.setdefault("sent", {})[str(i)] = d.isoformat()
        for t in themes:
            st.setdefault("themes", {})[t] = d.isoformat()
        st["recent"] = (st.get("recent", []) + [p[2:].strip() if p[:1] in "🎬📸" else p for p in prompts])[-60:]
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    msgs = ([head] + [f"{i}) {p}" for i, p in enumerate(prompts, 1)]) if prompts else []
    if "--show" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8"); print("\n---\n".join(msgs) or "nothing passed review"); sys.exit()
    api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    for m in msgs:
        req = urllib.request.Request(api, data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": m}).encode(),
                                     headers={"Content-Type": "application/json"})
        print(json.load(urllib.request.urlopen(req, timeout=30)).get("ok"))
    if not msgs:
        print("no prompt passed review; nothing sent")
