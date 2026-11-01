"""Public reply with the owner's offer card under Facebook Page comments (owner, 31 Oct).
DMs to people who only commented are blocked by Meta (each comment allows ONE private reply, Meta's own
automation already used it), so the public reply is how everyone till date gets the photo + number.
Replies to every top-level comment the Page hasn't answered yet, oldest first, max BATCH per run (spam-safe).
State: social/comment-state.json. Runs from messenger.yml every ~15 min.
  python social/comment_reply.py [--dry]
"""
import json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__)); STATE = os.path.join(BASE, "comment-state.json")
PAGE, V = "1296793536861294", "https://graph.facebook.com/v24.0"
PHOTO = ""  # 1 Nov: old card said FREE sample; text only until the new 199/- card is chosen
TEXT = 'Namaste ji 🙏\nVAJRA PP shuttering sheet: ₹3,500 + GST (8x4 ft, 12 mm).\n\nSample (1x1 ft) bhi milta hai, 199/-\n\nSample ya rate ke liye apna naam aur shehar bheje - call/WhatsApp karein: 83050 70160\n\n👉 https://vajraformwork.vercel.app/try'
BATCH = 20


def get(path, **p):
    return json.load(urllib.request.urlopen(f"{V}/{path}?" + urllib.parse.urlencode(p), timeout=60))


def main():
    dry = "--dry" in sys.argv
    pt = get(PAGE, fields="access_token", access_token=os.environ["META_TOKEN"])["access_token"]
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": []}
    done = set(st["done"]); todo = []
    for p in get(f"{PAGE}/posts", fields="id", limit=50, access_token=pt).get("data", []):
        try:
            cs, r = [], get(f"{p['id']}/comments", fields="id,created_time,from{id},comments.limit(25){from{id},message}", filter="toplevel", limit=100, access_token=pt)
            while True:
                cs += r.get("data", []); nxt = r.get("paging", {}).get("next")
                if not nxt: break
                r = json.load(urllib.request.urlopen(nxt, timeout=60))
        except Exception:
            continue
        for c in cs:
            if c["id"] in done or c.get("from", {}).get("id") == PAGE:
                continue
            if any(r.get("from", {}).get("id") == PAGE for r in c.get("comments", {}).get("data", [])):
                done.add(c["id"]); continue   # already answered publicly
            todo.append(c)
    todo.sort(key=lambda c: c["created_time"]); sent = 0
    for c in todo[:BATCH]:
        if not dry:
            try:
                d = urllib.parse.urlencode({"message": TEXT, "access_token": pt, **({"attachment_url": PHOTO} if PHOTO else {})}).encode()
                urllib.request.urlopen(urllib.request.Request(f"{V}/{c['id']}/comments", data=d), timeout=60); sent += 1
            except urllib.error.HTTPError as e:
                print("fail", c["id"], e.read().decode()[:150])
        done.add(c["id"])
    st["done"] = list(done)[-5000:]
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"))
    print(f"replied {sent}, left {max(0, len(todo) - BATCH)}")


if __name__ == "__main__":
    main()
