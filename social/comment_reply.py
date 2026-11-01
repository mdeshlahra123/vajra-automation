"""Public reply with the owner's offer card under Facebook Page comments (owner, 31 Oct).
DMs to people who only commented are blocked by Meta (each comment allows ONE private reply, Meta's own
automation already used it), so the public reply is how everyone till date gets the photo + number.
Replies to every top-level comment the Page hasn't answered yet, oldest first, max BATCH per run (spam-safe).
State: social/comment-state.json. Runs from messenger.yml every ~15 min.
  python social/comment_reply.py [--dry]
"""
import time, json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__)); STATE = os.path.join(BASE, "comment-state.json")
PAGE, V = "1296793536861294", "https://graph.facebook.com/v24.0"
PHOTO = "https://vajraformwork.vercel.app/social/msg-offer.jpg"  # offer card design 1: sample 199/-, sheet 3,400+GST trial (owner 1 Nov)
TEXT = 'Namaste ji 🙏\nVAJRA PP shuttering sheet: ₹3,500 + GST (8x4 ft, 12 mm).\n\nSample (1x1 ft) bhi milta hai, 199/-\n\nSample ya rate ke liye apna naam aur shehar bheje - call/WhatsApp karein: 83050 70160\n\n👉 https://vajraformwork.vercel.app/try'
DMBATCH = int(sys.argv[sys.argv.index("--dmtest") + 1]) if "--dmtest" in sys.argv else 60
BATCH = 60  # 1 Nov: 800+ comments on top FB reels; 60 per 15-min run, small gap to avoid Meta spam limits


def get(path, **p):
    return json.load(urllib.request.urlopen(f"{V}/{path}?" + urllib.parse.urlencode(p), timeout=60))


def main():
    dry = "--dry" in sys.argv
    pt = get(PAGE, fields="access_token", access_token=os.environ["META_TOKEN"])["access_token"]
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": []}
    done = set(st["done"]); todo = []; dmdone = set(st.get("dm", [])); dmtodo = []
    objs = get(f"{PAGE}/posts", fields="id", limit=50, access_token=pt).get("data", [])
    try:
        objs += get(f"{PAGE}/videos", fields="id", limit=30, access_token=pt).get("data", [])
    except Exception as e:
        print("videos list failed", str(e)[:100])
    for p in objs:
        try:
            cs, r = [], get(f"{p['id']}/comments", fields="id,created_time,from{id,name},comments.limit(25){from{id},message}", filter="toplevel", limit=100, access_token=pt)
            while True:
                cs += r.get("data", []); nxt = r.get("paging", {}).get("next")
                if not nxt: break
                r = json.load(urllib.request.urlopen(nxt, timeout=60))
        except Exception:
            continue
        for c in cs:
            if c.get("from", {}).get("id") != PAGE and c["id"] not in dmdone:
                dmtodo.append(c)
            if c["id"] in done or c.get("from", {}).get("id") == PAGE:
                continue
            if any(r.get("from", {}).get("id") == PAGE for r in c.get("comments", {}).get("data", [])):
                done.add(c["id"]); continue   # already answered publicly
            todo.append(c)
    todo.sort(key=lambda c: c["created_time"], reverse=True); sent = dm = 0
    if "--dmtest" in sys.argv: todo = []   # newest first: fresh commenters are hottest leads
    for c in todo[:BATCH]:
        if not dry:
            try:
                d = urllib.parse.urlencode({"message": TEXT, "access_token": pt, **({"attachment_url": PHOTO} if PHOTO else {})}).encode()
                urllib.request.urlopen(urllib.request.Request(f"{V}/{c['id']}/comments", data=d), timeout=60); sent += 1; time.sleep(1)
            except urllib.error.HTTPError as e:
                print("fail", c["id"], e.read().decode()[:150])
        done.add(c["id"])
    # 1 Nov: Meta's comment automation opens an empty chat but its private message stopped arriving.
    # Send the comment's one private reply ourselves (comments < 7 days, newest first). If Meta already used it,
    # Facebook refuses (#10900) and we skip, so nobody gets two.
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    dmtodo = [c for c in dmtodo if (now - datetime.datetime.strptime(c["created_time"], "%Y-%m-%dT%H:%M:%S%z")).days < 7]
    dmtodo = list({c["id"]: c for c in dmtodo}.values())   # posts + videos lists overlap
    dmtodo.sort(key=lambda c: c["created_time"], reverse=True)
    for c in dmtodo[:DMBATCH]:
        who = c.get("from", {}).get("name", c["id"])
        if not dry:
            try:
                body = json.dumps({"recipient": {"comment_id": c["id"]}, "message": {"text": TEXT}}).encode()
                urllib.request.urlopen(urllib.request.Request(f"{V}/{PAGE}/messages?access_token={pt}", data=body,
                                       headers={"Content-Type": "application/json"}), timeout=60); dm += 1
                print("dm ok", who); time.sleep(1); dmdone.add(c["id"])
            except urllib.error.HTTPError as e:
                err = e.read().decode()[:140]; print("dm skip", who, err)
                if '"code":10900' in err or "already" in err or '"code":551' in err:
                    dmdone.add(c["id"])   # Meta already used the one private reply / person unreachable: don't retry
    st["dm"] = list(dmdone)[-5000:]
    print(f"DM pass: {dm} sent, {max(0, len(dmtodo) - DMBATCH)} left")
    st["done"] = list(done)[-5000:]
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"))
    print(f"replied {sent}, DMs {dm}, left {max(0, len(todo) - BATCH)}")


if __name__ == "__main__":
    main()
