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

REVIEW = """You review prompts for Google Flow (Veo 3.1 / Gemini Omni Flash video) for VAJRA, a PP shuttering sheet brand
in Chhattisgarh, India. The clips are the PROBLEM part of an Instagram reel; our real product footage is added later.

For each draft, return a final prompt that a non-technical person can paste into Flow as is. Requirements:
- One clear shot, 8 seconds, vertical 9:16, realistic handheld phone-video look on an Indian construction site.
- Structure: camera/shot, subject, action, setting, light, then a "Sound:" line with ambient sound only.
- Plain simple English, 40-80 words, no jargon, no lists, nothing the model could misread.
- IF the shot shows shuttering/formwork boards, they must be BROWN wooden plywood. Never a grey or plastic sheet
  (that is our real product; AI must never fake it). General construction scenes (rebar, concrete pour, plaster,
  site views, a worried contractor) need no shuttering at all and are welcome.
- No product test or proof (no throwing, bending, nailing, water test of any sheet). No brand names, no text, signs,
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
        head_fmt = "🎬 Flow prompts – {} alag-alag video (9:16). Jo achhe lage bana ke yahin bhejo, caption: flow"
    else:   # 3 Nov fix: was IDEAS[day % len] -> same prompts came back every few days. Now least-recently-sent.
        chosen = pick(1, st)
        head_fmt = "🎬 Flow " + d.strftime('%d %b') + " – {} video (9:16). Bana ke yahin bhejo, caption: flow"
    prompts = []
    for i in chosen:
        prompts += review(IDEAS[i])
    head = head_fmt.format(len(prompts))
    if prompts and "--show" not in sys.argv:
        for i in chosen:
            st.setdefault("sent", {})[str(i)] = d.isoformat()
        json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
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
