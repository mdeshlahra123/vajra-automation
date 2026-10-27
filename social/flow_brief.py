"""Daily Google Flow brief to the Telegram group: what to make today with the free credits (~50/day).
Rotates through a bank of safe prompts (no recurring AI character, no fake proof, brown ply in problem shots,
no text in frame, 9:16). Results come back to the group: videos with caption "flow" -> make_real.py (AI label),
photos -> saved for posts.
  python social/flow_brief.py          send today's brief
  python social/flow_brief.py --show   print it only
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, sys, urllib.request

END = " Vertical 9:16, realistic documentary style, natural light. No text, no logos, no watermark."
# (kind, credits note, prompt)
BANK = [
    ("video", "Veo 3.1 Fast", "Close-up on an Indian construction site after rain: a stack of brown plywood shuttering sheets, swollen and peeling at the edges, water dripping, muddy ground, grey overcast light. Sound: dripping water, distant site noise. No faces."),
    ("video", "Veo 3.1 Fast", "Two Indian labourers in dusty clothes struggle to carry one heavy wet brown plywood sheet across a site, slow steps, seen from behind, hot afternoon sun. Sound: heavy breathing, footsteps on gravel."),
    ("video", "Omni Flash", "Slow push-in on a large pile of broken, cracked brown plywood shuttering boards thrown in the corner of a half-built Indian house, dust in sunlight. Sound: wind, distant hammering."),
    ("video", "Omni Flash", "A contractor's hand flips through a thick bill book and stops on a page, worried sigh, cement bags and brown plywood in the background, evening light, face not shown. Sound: paper rustle, sigh."),
    ("video", "Veo 3.1 Fast", "Brown plywood shuttering being pulled off a fresh concrete slab underside, the ply edge breaks and splinters, concrete surface rough. Sound: wood cracking. Faces not shown."),
    ("video", "Omni Flash", "Dawn over a half-built two-storey Indian house with scaffolding and bamboo props, birds, soft orange sky, slow drone-like rise. Sound: morning birds, faint traffic."),
    ("video", "Omni Flash", "Close-up of a rebar cage for a column being tied with wire by gloved hands, sparks of sunlight, dust. Sound: wire twisting, site ambience."),
    ("video", "Veo 3.1 Fast", "Concrete being poured from a pipe onto a slab at an Indian site, workers spreading it with shovels, wide shot from above. Sound: concrete pump, shovels."),
    ("video", "Omni Flash", "Monsoon rain hitting a construction site at night, brown plywood sheets lying in puddles, a tube light flickering. Sound: heavy rain."),
    ("video", "Omni Flash", "A truck unloading a messy stack of brown plywood sheets at a site, several sheets with broken corners fall, dust rises. Sound: thud, truck engine."),
    ("image", "Nano Banana", "Golden-hour photo of a clean Indian residential construction site with neat columns and scaffolding, empty space in the top third of the frame for text."),
    ("image", "Nano Banana", "Photo of a big pile of old damaged brown plywood shuttering boards next to a half-built house, gloomy light, empty space in the top third for text."),
    ("image", "Nano Banana", "Flat-lay photo of construction tools on a concrete floor: measuring tape, hammer, nails, trowel, gloves, soft shadows, empty space in the centre for text."),
    ("image", "Nano Banana", "Photo of a modern finished Indian house exterior with smooth concrete columns, bright day, empty sky area for text."),
]
TIPS = ("• Flow mein: Create → 9:16 (vertical) select karo.\n"
        "• Har video 6-8 sec. Pasand na aaye to ek baar hi dobara banao, credits bachao.\n"
        "• Kabhi mat banana: sheet phenkna/modna/keel/paani test (ye real hi chahiye). Grey sheet problem scene mein nahi.\n"
        "• Wapas bhejna: video(s) is group mein bhejo, PEHLE video ke caption mein likho: flow\n"
        "  Photos bhi bhej sakte ho (caption: flow). Main reel bana ke approval ke liye bhejunga.")


def brief(day=None):
    d = day or (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
    n = d.toordinal()
    vids = [b for b in BANK if b[0] == "video"]
    imgs = [b for b in BANK if b[0] == "image"]
    picks = [vids[(n * 2) % len(vids)], vids[(n * 2 + 1) % len(vids)], imgs[n % len(imgs)]]
    msgs = [f"🎬 Aaj ka Google Flow kaam ({d.strftime('%d %b')}), ~50 free credits:\n2 videos + 1 photo. Har prompt alag message mein hai, copy-paste karo.\n\n" + TIPS]
    for i, (kind, model, p) in enumerate(picks, 1):
        msgs.append(f"{i}) {'Video' if kind == 'video' else 'Photo'} ({model})")
        msgs.append(p + END)
    return msgs


if __name__ == "__main__":
    out = brief()
    if "--show" in sys.argv:
        print("\n---\n".join(out)); sys.exit()
    api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    for m in out:
        req = urllib.request.Request(api, data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": m}).encode(),
                                     headers={"Content-Type": "application/json"})
        print(json.load(urllib.request.urlopen(req, timeout=30)).get("ok"))
