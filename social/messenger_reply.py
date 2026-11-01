"""Auto-reply on Facebook Messenger (owner, 31 Oct: "too many messages, send them the sample photo + number").
For every Page conversation where the LAST message is from the customer and we haven't auto-replied to it yet
(and it is inside Meta's 24-hour reply window), send: the free-sample photo + a short text with the number.
Remembers replied message ids in social/messenger-state.json, so nobody gets it twice for the same message.
Only Facebook Messenger (Instagram DMs stay with Meta's own automation).
  python social/messenger_reply.py [--dry]
Env: META_TOKEN (user token with page access).
"""
import datetime, json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "messenger-state.json")
PAGE, V = "1296793536861294", "https://graph.facebook.com/v24.0"
PHOTO = "https://vajraformwork.vercel.app/social/msg-offer.jpg"  # offer card design 1: sample 199/-, sheet 3,400+GST trial (owner 1 Nov)
TEXT = 'Namaste ji 🙏\nVAJRA PP shuttering sheet: ₹3,500 + GST (8x4 ft, 12 mm).\n\nSample (1x1 ft) bhi milta hai, 199/-\n\nSample ya rate ke liye apna naam aur shehar bheje - call/WhatsApp karein: 83050 70160\n\n👉 https://vajraformwork.vercel.app/try'


def get(path, **p):
    return json.load(urllib.request.urlopen(f"{V}/{path}?" + urllib.parse.urlencode(p), timeout=60))


def post(path, tok, body):
    req = urllib.request.Request(f"{V}/{path}?access_token={tok}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def main():
    dry = "--dry" in sys.argv
    pt = get(PAGE, fields="access_token", access_token=os.environ["META_TOKEN"])["access_token"]
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": []}
    done = set(st["done"])
    convs = get(f"{PAGE}/conversations", platform="messenger", fields="updated_time,participants,messages.limit(1){id,message,from,created_time}",
                limit=100, access_token=pt).get("data", [])
    now = datetime.datetime.now(datetime.timezone.utc); sent = 0
    for c in convs:
        m = (c.get("messages", {}).get("data") or [None])[0]
        if not m or m["id"] in done or (m["from"]["id"] == PAGE and "--all" not in sys.argv):
            continue
        t = datetime.datetime.strptime(m["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        if (now - t).total_seconds() > 23 * 3600:   # outside Meta's 24 h window: can't message
            done.add(m["id"]); continue
        if m["from"]["id"] == PAGE:   # --all: find the customer in the participants
            psid = next((p["id"] for p in c.get("participants", {}).get("data", []) if p["id"] != PAGE), None)
            if not psid or psid in st.setdefault("offer", []):
                continue
            st["offer"].append(psid)
        else:
            psid = m["from"]["id"]
        print("reply to", m["from"].get("name"), "|", (m.get("message") or "")[:60])
        if not dry:
            try:
                if PHOTO: post(f"{PAGE}/messages", pt, {"recipient": {"id": psid}, "messaging_type": "RESPONSE",
                                              "message": {"attachment": {"type": "image", "payload": {"url": PHOTO, "is_reusable": True}}}})
                post(f"{PAGE}/messages", pt, {"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": TEXT}})
                sent += 1
            except urllib.error.HTTPError as e:
                print("  failed:", e.read().decode()[:200])
        done.add(m["id"])
    st["done"] = list(done)[-2000:]
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"))
    print("sent", sent, "of", len(convs), "conversations")


if __name__ == "__main__":
    main()
