"""Until the YouTube API audit is approved: send each reel posted today to the Telegram group
with a ready YouTube Shorts title + description, so someone uploads it from the YouTube app (~1 min).

  python social/yt_tg.py            send today's posted reels not sent yet (run after daily-post)
  python social/yt_tg.py <queue-id> send that one now (manual / resend)

Marks queue items with "yt_tg": <date>. Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, sys, urllib.request

SOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SOC)
from yt_upload import meta  # same title/description the API uploader will use

API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/"
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def call(method, **p):
    req = urllib.request.Request(API + method, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:300]}


def send(it):
    title, desc, tags = meta(it)
    ai = "\n⚠️ AI wali video: upload karte waqt 'Altered or synthetic content' = YES karna." if it.get("ai") else ""
    head = ("📺 YouTube Short – aaj ki reel\n1) Video save karo  2) YouTube app → + → Short → ye video\n"
            "3) Neeche wala TITLE aur DESCRIPTION copy-paste karo  4) Audience: 'Not made for kids'" + ai)
    r = call("sendVideo", chat_id=CHAT, video=it["video"], caption=head, supports_streaming=True)
    if not r.get("ok"):  # too big or URL fetch failed: send the link instead
        r = call("sendMessage", chat_id=CHAT, text=head + "\nVideo: " + it["video"])
    call("sendMessage", chat_id=CHAT, text=title)
    call("sendMessage", chat_id=CHAT, text=desc[:4000])
    print("sent", it["id"], r.get("ok"))
    return r.get("ok")


if __name__ == "__main__":
    p = os.path.join(SOC, "queue.json")
    q = json.load(open(p, encoding="utf-8"))
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
    if len(sys.argv) > 1:
        items = [x for x in q["posts"] if x["id"] == sys.argv[1]]
    else:
        items = [x for x in q["posts"] if x.get("video") and x.get("posted") == today and not x.get("yt_tg")]
    for it in items:
        if send(it):
            it["yt_tg"] = today
    json.dump(q, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a", encoding="utf-8").write("\n")
