"""Telegram approval for VAJRA content.

  python social/tg.py send <id>   send pending item <id> (from social/pending.json) to the approval group
  python social/tg.py poll        read button taps; Approve -> add to queue.json, Reject -> drop

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. State lives in social/pending.json and social/tg-offset.txt.
pending.json: {"items": [{"id", "video" or "image", "caption" (path), "title", "position": "end"|"next",
                          "status": "draft"|"sent"|"approved"|"rejected", "msg_id", "by", "at"}]}
"""
import json, os, sys, urllib.request, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PENDING, QUEUE, OFFSET = (os.path.join(BASE, f) for f in ("pending.json", "queue.json", "tg-offset.txt"))
API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/"
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def call(method, **p):
    req = urllib.request.Request(API + method, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:500]}


def upload(method, field, path, **fields):
    """multipart/form-data upload of one file (Telegram bots: up to 50 MB)."""
    b = "----vajra" + os.urandom(8).hex()
    body = b""
    for k, v in fields.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(path)}"\r\n'
             f"Content-Type: video/mp4\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(API + method, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:500]}


def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M")


def send(item_id):
    pend = load(PENDING, {"items": []})
    it = next((i for i in pend["items"] if i["id"] == item_id), None)
    if not it:
        sys.exit(f"no pending item {item_id}")
    cap = open(os.path.join(BASE, it["caption"]), encoding="utf-8").read().strip()
    text = f"🆕 {it.get('title', it['id'])}\n\nCaption:\n{cap}"[:1000]
    kb = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"ok:{it['id']}"},
                               {"text": "❌ Reject", "callback_data": f"no:{it['id']}"}]]}
    if it.get("file"):
        r = upload("sendVideo", "video", os.path.join(BASE, "..", it["file"]), chat_id=CHAT, caption=text,
                   reply_markup=json.dumps(kb), supports_streaming="true")
    elif it.get("video"):
        r = call("sendVideo", chat_id=CHAT, video=it["video"], caption=text, reply_markup=kb, supports_streaming=True)
    else:
        r = call("sendPhoto", chat_id=CHAT, photo=it["image"], caption=text, reply_markup=kb)
    if not r.get("ok"):
        sys.exit(f"send failed: {r}")
    it.update(status="sent", msg_id=r["result"]["message_id"], sent_at=now())
    save(PENDING, pend)
    print("sent", item_id, "msg", it["msg_id"])


def add_to_queue(it):
    q = load(QUEUE, {"posts": []})
    if any(p["id"] == it["id"] for p in q["posts"]):
        return
    entry = {"id": it["id"], "caption": it["caption"], "posted": ""}
    if it.get("file"):
        # made by the engine: approve.yml copies the file to the website repo; Instagram fetches it from there
        entry["video"] = "https://vajraformwork.vercel.app/social/" + os.path.basename(it["file"])
        if it.get("ai"):
            entry["ai"] = True
        it["publish"] = "todo"
    else:
        entry["video" if it.get("video") else "image"] = it.get("video") or it.get("image")
    posts = q["posts"]
    if it.get("position") == "next":
        kind = bool(it.get("video"))
        idx = next((n for n, p in enumerate(posts) if not p.get("posted") and bool(p.get("video")) == kind), len(posts))
        posts.insert(idx, entry)
    else:
        posts.append(entry)
    save(QUEUE, q)


def poll():
    offset = int(open(OFFSET).read().strip()) if os.path.exists(OFFSET) else 0
    wh = call("getWebhookInfo").get("result", {})
    if wh.get("url"):
        print("webhook is set (instant mode via Apps Script); polling not needed"); return
    r = call("getUpdates", offset=offset, timeout=0, allowed_updates=["callback_query", "message", "my_chat_member"])
    if not r.get("ok"):
        print("getUpdates failed:", r)
    print("updates received:", len(r.get("result", [])), "offset", offset)
    pend = load(PENDING, {"items": []})
    changed = 0
    for u in r.get("result", []):
        offset = u["update_id"] + 1
        cq = u.get("callback_query")
        if not cq:
            print("update (not a tap):", list(u.keys())[1:], json.dumps(u)[:200])
            continue
        chat_id = str(cq.get("message", {}).get("chat", {}).get("id"))
        print("tap:", cq.get("data"), "from", cq["from"].get("first_name"), "chat", chat_id)
        if chat_id != str(CHAT):
            call("answerCallbackQuery", callback_query_id=cq["id"], text="Unknown chat")
            print("  skipped: chat id differs from TELEGRAM_CHAT_ID", CHAT)
            continue
        who = cq["from"].get("first_name", "someone")
        action, _, item_id = cq.get("data", "").partition(":")
        it = next((i for i in pend["items"] if i["id"] == item_id), None)
        if action == "test" or not it:
            call("answerCallbackQuery", callback_query_id=cq["id"], text="Test button, nothing to do.")
            continue
        if it["status"] in ("approved", "rejected"):
            call("answerCallbackQuery", callback_query_id=cq["id"], text=f"Already {it['status']} by {it.get('by')}")
            continue
        ok = action == "ok"
        it.update(status="approved" if ok else "rejected", by=who, at=now())
        if ok and not it.get("test"):
            add_to_queue(it)
        changed += 1
        label = f"✅ Approved by {who}, added to queue" if ok else f"❌ Rejected by {who}"
        call("answerCallbackQuery", callback_query_id=cq["id"], text=label)
        call("editMessageReplyMarkup", chat_id=CHAT, message_id=cq["message"]["message_id"],
             reply_markup={"inline_keyboard": [[{"text": label, "callback_data": "done"}]]})
        print(label, item_id)
    with open(OFFSET, "w") as f:
        f.write(str(offset))
    if changed:
        save(PENDING, pend)
    print("poll done, changes:", changed)


def tap(arg):
    """Instant mode: Apps Script already answered the tap and passes 'ok:<id>|<name>|<message_id>'."""
    data, who, msg_id = (arg.split("|") + ["", "", ""])[:3]
    action, _, item_id = data.partition(":")
    pend = load(PENDING, {"items": []})
    it = next((i for i in pend["items"] if i["id"] == item_id), None)
    def button(label):
        call("editMessageReplyMarkup", chat_id=CHAT, message_id=int(msg_id),
             reply_markup={"inline_keyboard": [[{"text": label, "callback_data": "done"}]]})
    if not it:
        print("unknown item", item_id); button("⚠️ Unknown item"); return
    if it["status"] in ("approved", "rejected"):
        print("already", it["status"]); button(f"{'✅' if it['status'] == 'approved' else '❌'} Already {it['status']} by {it.get('by')}"); return
    ok = action == "ok"
    it.update(status="approved" if ok else "rejected", by=who or "someone", at=now())
    if ok and not it.get("test"):
        add_to_queue(it)
    save(PENDING, pend)
    label = f"✅ Approved by {it['by']}, added to queue" if ok else f"❌ Rejected by {it['by']}"
    button(label); print(label, item_id)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "send":
        send(sys.argv[2])
    elif cmd == "tap":
        tap(sys.argv[2])
    elif cmd == "poll":
        poll()
    elif cmd == "unhook":
        print("deleteWebhook:", call("deleteWebhook", drop_pending_updates=False))
    elif cmd == "debug":
        print("me:", call("getMe").get("result", {}).get("username"))
        print("webhook:", json.dumps(call("getWebhookInfo").get("result", {})))
        print("chat:", json.dumps(call("getChat", chat_id=CHAT).get("result", call("getChat", chat_id=CHAT)))[:400])
        r = call("getUpdates", timeout=0, allowed_updates=["callback_query", "message", "my_chat_member", "chat_member"])
        print("raw updates (no offset):", len(r.get("result", [])), json.dumps(r)[:1500])
    else:
        sys.exit(__doc__)
