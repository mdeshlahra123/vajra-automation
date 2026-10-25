"""Once a day (before the reel post): copy approved engine reels to the website and remove reel videos that are
no longer needed (already posted or not in the queue). One website push per day at most, to save Vercel storage.
Only touches website/social/*.mp4 (root). Never touches social/web/ (used by /photos). Needs WEBSITE_TOKEN."""
import json, os, shutil, subprocess, sys, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
pend_path, queue_path = os.path.join(BASE, "pending.json"), os.path.join(BASE, "queue.json")
pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
queue = json.load(open(queue_path, encoding="utf-8"))
todo = [i for i in pend["items"] if i.get("publish") == "todo"]
keep = {os.path.basename(p.get("video") or p["reel"]) for p in queue["posts"] if not p.get("posted") and (p.get("video") or p.get("reel"))}

url = f"https://x-access-token:{os.environ['WEBSITE_TOKEN']}@github.com/mdeshlahra123/vajraformwork.git"
subprocess.run(["git", "clone", "-q", "--depth", "1", url, "site"], check=True)
sdir = os.path.join("site", "social")
for i in todo:
    shutil.copy(os.path.join(BASE, "..", i["file"]), os.path.join(sdir, os.path.basename(i["file"])))
    i["publish"] = "done"
removed = [f for f in os.listdir(sdir) if f.endswith(".mp4") and f not in keep and not any(os.path.basename(i["file"]) == f for i in todo)]
for f in removed:
    os.remove(os.path.join(sdir, f))
print("add:", [i["id"] for i in todo], "| remove:", removed)
# public next.json: upcoming posts with dates, read by the Telegram bot for instant "aaj/kal konsi reel" answers
import datetime
today = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
def hook(p):
    try:
        return open(os.path.join(BASE, p["caption"]), encoding="utf-8").read().strip().split("\n")[0][:120]
    except Exception:
        return ""
pend_posts = [p for p in queue["posts"] if not p.get("posted")]
nxt = {"made": str(today), "reels": [], "images": []}
for kind, key, t in (("reels", "video", "09:30"), ("images", "image", "19:30")):
    for n, p in enumerate([p for p in pend_posts if p.get(key)][:7]):
        nxt[kind].append({"date": str(today + datetime.timedelta(days=n)), "time": t, "id": p["id"], "url": p[key], "hook": hook(p)})
npath = os.path.join(sdir, "next.json")
old = open(npath, encoding="utf-8").read() if os.path.exists(npath) else ""
new = json.dumps(nxt, ensure_ascii=False, indent=1)
if new != old:
    open(npath, "w", encoding="utf-8").write(new)
if not todo and not removed and new == old:
    sys.exit(0)
g = lambda *a: subprocess.run(["git", "-C", "site", *a], check=True)
g("config", "user.name", "vajra-bot"); g("config", "user.email", "vajra-bot@users.noreply.github.com")
g("add", "-A", "social"); g("commit", "-q", "-m", f"bot: daily reels +{len(todo)} -{len(removed)}"); g("push", "-q")
json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# wait until the newest added reel is live, so today's post can fetch it
for i in todo[-1:]:
    u = "https://vajraformwork.vercel.app/social/" + os.path.basename(i["file"])
    for _ in range(30):
        try:
            urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=20); print("live:", u); break
        except Exception:
            time.sleep(10)
