"""Peek at recent video messages in the Telegram group WITHOUT consuming updates (negative offset is a
non-destructive peek; it does not advance the Apps Script's offset). Prints file_id + caption + time.
Read-only. Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID."""
import json, os, urllib.request, urllib.parse, datetime
API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/"
CHAT = str(os.environ["TELEGRAM_CHAT_ID"])
# negative offset = last N updates, peek only (does not confirm/consume them)
url = API + "getUpdates?" + urllib.parse.urlencode({"offset": -40, "timeout": 0,
      "allowed_updates": json.dumps(["message"])})
r = json.load(urllib.request.urlopen(url, timeout=60))
out = []
for u in r.get("result", []):
    m = u.get("message") or {}
    if str(m.get("chat", {}).get("id")) != CHAT:
        continue
    doc = m.get("document") or {}
    vid = m.get("video") or (doc if doc.get("mime_type", "").startswith("video") else None)
    if vid:
        t = datetime.datetime.utcfromtimestamp(m["date"] + 19800).strftime("%d %b %H:%M")
        out.append({"t": t, "file_id": vid["file_id"], "secs": vid.get("duration"),
                    "cap": (m.get("caption") or "").replace("\n", " ")[:50],
                    "from": m.get("from", {}).get("first_name", "")})
print(json.dumps(out, ensure_ascii=False, indent=1))
print("COUNT", len(out))
