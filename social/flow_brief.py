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


def today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()


if __name__ == "__main__":
    d = today()
    if "--batch" in sys.argv:   # one-off varied batch: review N idea sets across the themes and send them together
        try:
            n = int(sys.argv[sys.argv.index("--batch") + 1])
        except (ValueError, IndexError):
            n = 4
        prompts = []
        for idea in IDEAS[:max(1, n)]:
            prompts += review(idea)
        head = f"🎬 Flow prompts – {len(prompts)} alag-alag video (9:16). Jo achhe lage bana ke yahin bhejo, caption: flow"
    else:
        prompts = review(IDEAS[d.toordinal() % len(IDEAS)])
        head = f"🎬 Flow {d.strftime('%d %b')} – {len(prompts)} video (9:16). Bana ke yahin bhejo, caption: flow"
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
