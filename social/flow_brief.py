"""Daily Google Flow brief to the Telegram group: ONE reel idea per day, with 2 shots to make in Flow
(~40-50 of the 50 free daily credits). Each shot has a Hindi line saying what it is and why it's needed.
The AI shots are only the PROBLEM part; the reel ends on our real VAJRA footage (added by make_real.py).
Rules: no recurring AI character, no fake proof (throw/bend/nail/water), problem shots show brown ply only,
no text in frame, 9:16.
  python social/flow_brief.py          send today's brief
  python social/flow_brief.py --show   print it only
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, sys, urllib.request

END = " Vertical 9:16 video, 8 seconds, realistic, like a phone video shot on an Indian construction site. No text, no logos."

# Each idea: title, what the finished reel will be (Hindi), [(what this shot is in Hindi, English prompt), ...]
IDEAS = [
    ("Barish ke baad ply",
     "Reel: barish ke baad ply phool gayi, kharab ho gayi → end mein VAJRA sheet (paani se kharab nahi hoti).",
     [("Barish mein bheegi, phooli hui ply ka dher (problem dikhana)",
       "Close-up of a stack of brown plywood shuttering boards on a construction site after heavy rain, the edges swollen and peeling, water dripping off them, muddy ground. Sound of dripping water."),
      ("Thekedar bheegi ply dekh ke pareshan (reaction)",
       "An Indian contractor in a shirt looks at wet, damaged brown plywood boards and shakes his head in frustration, rainy grey sky. Sound of light rain.")]),
    ("Bhaari ply, 2 aadmi",
     "Reel: ek ply uthane ko 2 mazdoor lagte hain → end mein VAJRA sheet ek aadmi utha leta hai (real video).",
     [("2 mazdoor mushkil se ek bhaari ply utha rahe hain",
       "Two Indian labourers in dusty clothes struggle to lift and carry one heavy brown plywood shuttering board across a construction site, slow tired steps, hot sun. Sound of heavy breathing."),
      ("Ek mazdoor thak ke baith gaya, paseena",
       "A tired Indian construction labourer sits down next to a pile of brown plywood boards, wipes sweat from his forehead, hot afternoon. Sound of site noise.")]),
    ("Toota ply ka kachra",
     "Reel: har kuch slab ke baad ply toot ke kachra ban jaati hai → end mein VAJRA sheet dho ke phir use.",
     [("Tooti hui ply ka bada dher, kone mein pada",
       "Slow camera move toward a big pile of broken, cracked brown plywood shuttering boards thrown in the corner of a half-built Indian house, dust in the sunlight. Sound of wind."),
      ("Slab ke neeche se ply nikalte waqt toot jaati hai",
       "Workers pull a brown plywood board off the underside of a concrete slab and the board cracks and splinters. Sound of wood breaking.")]),
    ("Kharcha ka hisaab",
     "Reel: thekedar ply ke bill dekh ke pareshan → end mein VAJRA sheet (ply se 2-3 guna zyada chalti hai, sahi handling ke saath).",
     [("Thekedar bill book dekh ke sir pakad leta hai",
       "An Indian contractor sits at a small table at a construction site, looks at a bill book and holds his head in worry, brown plywood stacked behind him, evening light. Sound of a sigh."),
      ("Truck se nayi ply utar rahi hai, phir se",
       "A small truck unloads a stack of new brown plywood boards at an Indian construction site, workers carry them off. Sound of truck engine and boards dropping.")]),
    ("Site ki subah",
     "Reel: site ki khoobsurat shuruaat (mood) → phir humare real VAJRA column/slab clips. Evening reel ke liye.",
     [("Subah ka adhoora ghar, scaffolding, sooraj nikal raha",
       "Sunrise over a half-built two-storey Indian house with bamboo props and scaffolding, birds flying, soft orange light, slow rising camera. Sound of morning birds."),
      ("Column ke liye sariya bandhte haath",
       "Close-up of gloved hands tying steel rebar for a column with wire at an Indian construction site, morning sunlight. Sound of wire twisting.")]),
    ("Dhalai ka din",
     "Reel: dhalai (concrete pour) ka din → end mein VAJRA sheet par dhalai, smooth finish (real clip).",
     [("Slab par concrete daal rahe hain, upar se",
       "Wide shot from above of workers pouring and spreading concrete on a slab at an Indian construction site with shovels. Sound of concrete mixer and shovels."),
      ("Mixer machine ghoom rahi, site ka shor",
       "A concrete mixer machine turning at an Indian construction site, a worker adds cement, dust in the air. Sound of the mixer.")]),
]
TIPS = ("Kaise karna hai:\n"
        "1) flow.google kholo → video ke liye 9:16 (vertical) chuno\n"
        "2) Neeche diya English prompt copy karke Flow mein paste karo → Create\n"
        "3) Dono videos download karke is group mein bhejo, PEHLI video ke caption mein likho: flow\n"
        "Main inko reel mein jod ke end mein humari real VAJRA video lagaunga, phir approval ke liye bhejunga.\n"
        "⚠️ Flow se kabhi sheet phenkna/modna/keel/paani test mat banana. Wo real hi chahiye.")


def brief(day=None):
    d = day or (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()
    title, what, shots = IDEAS[d.toordinal() % len(IDEAS)]
    msgs = [f"🎬 Aaj ka Flow kaam ({d.strftime('%d %b')}): \"{title}\"\n\n{what}\n\nSirf 2 video banani hain (~40 free credits).\n\n{TIPS}"]
    for i, (hindi, prompt) in enumerate(shots, 1):
        msgs.append(f"Video {i}: {hindi}\n👇 Ye copy karo:")
        msgs.append(prompt + END)
    return msgs


if __name__ == "__main__":
    out = brief()
    if "--show" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8"); print("\n---\n".join(out)); sys.exit()
    api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    for m in out:
        req = urllib.request.Request(api, data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": m}).encode(),
                                     headers={"Content-Type": "application/json"})
        print(json.load(urllib.request.urlopen(req, timeout=30)).get("ok"))
