"""DAILY SKIT/DIALOGUE PROMPTS for Gemini Flow (no voiceover needed).
These are CHARACTER CONVERSATIONS - contractor, labour, engineer talking to each other.
Each reel = 3 parts (30 sec total when extended in Flow), ending with PP reveal + follow card.

Based on competitor analysis:
- Contractor-labour skits (funny misunderstandings, worker wisdom)
- Site confusion moments (wrong material ordered, measurements off)
- Before/after reactions (ply vs PP results)
- Indian construction comedy tropes (tea break conversations, site gossip)

Usage:
  python social/engine/skit_prompts.py           generate + send today's prompts (3 parts)
  python social/engine/skit_prompts.py --show    print only, don't send
"""
import datetime, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem

MODEL = "gemini-3.5-flash-lite"  # free tier

# SKIT SCENARIOS (each has 3 parts that form one story)
# Part 1 = setup (problem/question), Part 2 = middle (reaction/discussion), Part 3 = resolution (PP answer)
SCENARIOS = [
    {
        "title": "Contractor ka budget tension",
        "parts": [
            "Indian contractor at a dusty site table, looking stressed at a thick bill book and calculator, brown plywood stacked behind. Dialogue: 'Yaar shuttering ka kharcha dekho, har mahine nayi ply... khatam hi nahi hota'",
            "His engineer sits next to him, also worried, flipping through papers. Dialogue: 'Aur jo tooti hui ply hai, wo sab waste. Labour ka time bhi ja raha'",
            "Same contractor now smiling, pointing at a neat stack of grey PP sheets in the godown. Dialogue: 'Ab ye dekho! Ek baar le lo, baar-baar chalti hai, paisa bach gaya'"
        ]
    },
    {
        "title": "Labour ke liye halka hai",
        "parts": [
            "Two Indian labourers struggling to carry one heavy brown plywood board across a site, straining, slow walk. Dialogue: 'Bhai sambhal ke, bhaari hai ye toh... dono ko pakad'",
            "They set it down, tired, wiping sweat. One labourer says: 'Har baar isi chakkar mein peeth dard... do-do aadmi chahiye'",
            "One labourer alone easily carrying a grey PP sheet on his shoulder, walking fast, smiling. Dialogue: 'Arre bhai, ye toh akele uthati hai! Itni halki plastic... koi problem nahi'"
        ]
    },
    {
        "title": "Ply tooti, contractor gussa",
        "parts": [
            "Indian contractor inspecting a broken cracked brown plywood board on the ground, shaking his head. Dialogue: 'Yaar ye phir se toot gayi? Abhi toh do din pehle nayi li thi'",
            "Labour nearby shrugging, looking helpless. Dialogue: 'Saab dekho khud, de-shuttering mein hi crack ho gayi. Dubara nahi chalegi'",
            "Same contractor now calm, holding a grey PP sheet, tapping it. Dialogue: 'Ye plastic sheet strong hai bhai, dus baar bhi chala lo... tootti nahi'"
        ]
    },
    {
        "title": "Barish mein ply kharab",
        "parts": [
            "Indian contractor and labour standing in light rain, looking at a pile of wet brown plywood boards swollen and peeling. Dialogue: 'Saab ye sab kharab ho gayi, paani se phool gayi hai'",
            "Contractor holding his head, frustrated. Dialogue: 'Ab kya karein? Nayi leni padegi phir se, full paisa barbaad'",
            "Labourer hosing down a grey PP sheet, water sliding off clean. Dialogue: 'Ye plastic sheet paani se kuch nahi hota saab, dho ke dubara laga do bas'"
        ]
    },
    {
        "title": "Engineer ko smooth finish chahiye",
        "parts": [
            "Indian engineer running his hand over a rough concrete column with honeycomb patches, frowning. Dialogue: 'Ye kya hai? Finish itni kharab... client complaint karega'",
            "Contractor nearby explaining defensively. Dialogue: 'Saab ply purani thi, uska surface hi uneven tha... kya karein'",
            "Engineer nodding, smiling, touching a smooth finished column. Dialogue: 'Ab ye dekho! Plastic sheet se bilkul smooth finish aati hai, ek dum perfect'"
        ]
    },
    {
        "title": "Labour ki site gossip - PP",
        "parts": [
            "Two Indian labourers sitting on bricks during chai break at a site, holding small glasses, talking. Dialogue: 'Bhai tune suna? Bagal wali site pe plastic sheet use kar rahe'",
            "Other labour curious, leaning in. Dialogue: 'Haan yaar, dekha maine. Ek aadmi akele uthata hai... ply se bahut halki hoti'",
            "Both laughing, nodding. Dialogue: 'Aur wo dho ke phir se lagati bhi... apan ko bhi wohi chahiye re!'"
        ]
    },
    {
        "title": "Mistri ka naya idea",
        "parts": [
            "Indian mason (mistri) looking at a brown plywood board, measuring with a tape, shaking his head. Dialogue: 'Saab ye size galat hai, isme column nahi banega'",
            "Contractor worried, standing next to him. Dialogue: 'Toh ab kya karein? Nayi ply katni padegi... time waste'",
            "Mistri smiling, holding a grey PP sheet, showing it's easy to cut. Dialogue: 'Ye plastic sheet cutter se aaram se kat jaati hai bhai, jitna size chahiye utna'"
        ]
    },
    {
        "title": "Client visit - finish surprise",
        "parts": [
            "Indian client (well-dressed man) walking through a construction site with the contractor, looking around. Dialogue: 'Theek chal raha hai kaam?'",
            "Contractor nervously showing an old rough concrete wall. Dialogue: 'Ji saab, lekin finish sometimes thoda...'",
            "Client surprised, touching a new smooth column, smiling. Dialogue: 'Arre wah! Ye toh bilkul smooth hai... kaunsa shuttering use kiya?'"
        ]
    },
    {
        "title": "De-shuttering tension",
        "parts": [
            "Two Indian labourers carefully removing brown plywood from a column, it cracks, splinters. Dialogue: 'Arre arre dhyaan se! Toot gayi... ab ye chalegi nahi'",
            "Contractor watching, holding his head. Dialogue: 'Yaar har baar yahi problem... de-shuttering mein half damage ho jaati'",
            "One labour easily pulling off a grey PP sheet, clean. Dialogue: 'Ye plastic sheet seedha nikal aati hai saab, koi tension nahi'"
        ]
    },
    {
        "title": "Junior engineer training",
        "parts": [
            "Senior Indian engineer showing a junior engineer around a site, pointing at stacked brown plywood. Dialogue: 'Ye ply hai, cost zyada lagta... 8-10 baar hi chalti maximum'",
            "Junior engineer nodding, taking notes on a clipboard. Dialogue: 'Toh fir better option kya hai sir?'",
            "Senior engineer holding a grey PP sheet, explaining. Dialogue: 'Ye plastic sheet, bahut baar chalti hai... smooth finish bhi aati. Modern technique hai'"
        ]
    },
    # More scenarios (rotate daily, never repeat within 30 days)
    {
        "title": "Site pe naya labour",
        "parts": [
            "New young Indian labourer arriving at a site, looking confused at stacked materials. Dialogue: 'Bhai wo brown boards konsi jagah rakhni hai?'",
            "Senior labour laughing, pointing. Dialogue: 'Arre wo purani ply hai... ab use hi nahi karte. Wo grey plastic sheet use karo'",
            "New labour carrying a PP sheet easily, surprised. Dialogue: 'Arre ye toh itni halki hai! Purani ply se toh bahut aasan'"
        ]
    },
    {
        "title": "Thekedar ka cost comparison",
        "parts": [
            "Indian contractor with two site registers, comparing numbers, looking stressed. Dialogue: 'Is mahine ply mein 50 hazaar... pichle mahine bhi 45'",
            "His accountant next to him, also worried. Dialogue: 'Saab agar ye cost control nahi hua toh profit hi khatam'",
            "Same contractor showing the accountant a PP receipt, smiling. Dialogue: 'Ye dekho, ek baar mein le liya... ab mahino tak nahi leni'"
        ]
    },
    {
        "title": "Column ka finish check",
        "parts": [
            "Indian engineer with a torch, closely inspecting a concrete column, finding rough patches. Dialogue: 'Ye patches kyun hain? Finish smooth nahi hai'",
            "Contractor explaining nervously. Dialogue: 'Saab wo ply ka surface uneven tha... uska asar aa gaya'",
            "Engineer nodding at a different smooth column, satisfied. Dialogue: 'Aur ye column perfect hai! Plastic sheet se kaam kiya na?'"
        ]
    },
    {
        "title": "Site meeting - material review",
        "parts": [
            "Three contractors sitting in a site office, discussing, papers spread. Dialogue: 'Bhai shuttering mein kya use kar rahe ho要? Ply bahut mehnga pad raha'",
            "Second contractor agreeing. Dialogue: 'Haan yaar, aur har project mein nayi leni padti... reuse nahi hoti'",
            "Third contractor showing a grey PP sheet sample. Dialogue: 'Maine ye plastic sheet try kiya, bahut better hai... ek baar investment, fir peace'"
        ]
    },
    {
        "title": "Surprise inspection",
        "parts": [
            "Government inspector arriving at a site, checking materials with a contractor. Dialogue: 'Ye quality standards follow ho rahe hain?'",
            "Contractor showing different materials nervously. Dialogue: 'Ji sir, best quality ply use karte hain... lekin cost...'",
            "Inspector examining a smooth column made with PP sheets, impressed. Dialogue: 'Wah, ye finish toh bahut achha hai. Ye modern technique hai na?'"
        ]
    },
]

GEN_PROMPT = """You write 3-part dialogue skit prompts for Google Flow (Gemini Omni Flash video) for VAJRA PP shuttering sheets.
Today's angle: {angle}

Create 3 video prompts that tell ONE story in 3 parts (setup, middle, resolution). Each part = 10 seconds when extended, vertical 9:16, realistic.

CHARACTERS (Indian construction site):
- Contractor (30-45 age, casual shirt/jeans, worried about money/time)
- Labour/mason (25-40 age, work clothes, practical wisdom)
- Engineer (25-50 age, shirt with hard hat, technical guy)
- Client (well-dressed, checks work quality)

DIALOGUE RULES:
- Hinglish (Hindi + English mix, like real site talk)
- 1-2 short lines per part, natural conversation
- Part 1 = problem setup (ply issues: cost, weight, breaking, rough finish, water damage)
- Part 2 = reaction/discussion (worried faces, explaining problem)
- Part 3 = PP answer/resolution (showing grey PP sheets, happy/relieved, benefits mentioned)

VISUAL RULES:
- Each part: single continuous shot, handheld phone video look, Indian construction site background
- Brown plywood = old/problem material (Part 1-2 only)
- Grey PP hollow plastic sheets = solution (Part 3 only, plain with NO text/logo/printing)
- Real people talking naturally, ambient site sounds (tools, birds, distant traffic)
- Structure each as: "Shot: <camera>, Characters: <who>, Dialogue: '<what they say>', Setting: <where>, Sound: <ambient>"

Return JSON only: {{"parts":[{{"prompt":"..."}},{{"prompt":"..."}},{{"prompt":"..."}}]}}"""

ANGLES = [
    "contractor stress about ply cost eating profit",
    "labour tired carrying heavy plywood vs easy PP sheet",
    "ply breaking during de-shuttering disaster",
    "monsoon rain damaging stacked plywood boards",
    "engineer wants smooth finish, old ply gives rough surface",
    "tea break gossip about neighbour using PP sheets",
    "mistri cutting problems with ply vs PP",
    "client visiting site, surprised by smooth column finish",
    "de-shuttering tension, ply cracks",
    "senior training junior engineer about materials",
    "new labour first day, learns PP is lighter",
    "cost comparison meeting between contractors",
    "quality inspection surprise with smooth finish",
    "site meeting discussing material costs",
    "government inspector checking quality standards",
]

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skit-prompts-state.json")


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"used_angles": {}, "recent_prompts": []}


def pick_angle(st):
    """Pick least recently used angle."""
    import random
    used = st.get("used_angles", {})
    angles_sorted = sorted(ANGLES, key=lambda a: (used.get(a, "0000-00-00"), random.random()))
    return angles_sorted[0]


def generate(angle, st):
    """Generate 3-part skit prompt."""
    r = gem.text(MODEL, GEN_PROMPT.format(angle=angle), json_mode=True)
    parts = []
    for p in r.get("parts", [])[:3]:
        prompt = (p.get("prompt") or "").strip()
        if 40 <= len(prompt.split()) <= 150:  # longer than Flow b-roll, has dialogue
            parts.append(prompt)
    return parts


def today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()


if __name__ == "__main__":
    d = today()
    st = load_state()
    
    angle = pick_angle(st)
    
    try:
        parts = generate(angle, st)
    except Exception as e:
        print(f"Generate failed: {str(e)[:200]}")
        # Fallback to first unused scenario from the bank
        used_scenarios = set(st.get("used_angles", {}).keys())
        unused = [s for s in SCENARIOS if s["title"] not in used_scenarios]
        if unused:
            scenario = unused[0]
            parts = scenario["parts"]
            angle = scenario["title"]
        else:
            parts = SCENARIOS[0]["parts"]
            angle = SCENARIOS[0]["title"]
    
    if not parts or len(parts) < 3:
        print("Not enough parts generated, using bank fallback")
        parts = SCENARIOS[0]["parts"]
        angle = SCENARIOS[0]["title"]
    
    head = f"🎬🗣️ SKIT PROMPT – {angle}\n\n3 parts (extend each to 10 sec in Flow, total ~30 sec). Paste karo ek-ek karke:\n"
    msgs = [head] + [f"Part {i+1}/3:\n{p}\n" for i, p in enumerate(parts[:3])]
    
    if "--show" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n---\n".join(msgs))
        sys.exit()
    
    # Save state
    st.setdefault("used_angles", {})[angle] = d.isoformat()
    st.setdefault("recent_prompts", []).extend(parts[:3])
    st["recent_prompts"] = st["recent_prompts"][-90:]  # keep last 30 skits
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    
    # Send to Telegram
    api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    full_msg = "\n".join(msgs)
    req = urllib.request.Request(
        api,
        data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": full_msg}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        result = json.load(urllib.request.urlopen(req, timeout=30))
        print(f"Sent skit prompt: {angle}")
        print(f"Telegram response: {result.get('ok')}")
    except Exception as e:
        print(f"Failed to send: {str(e)[:200]}")
