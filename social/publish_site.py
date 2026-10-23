"""Once a day (before the reel post): copy approved engine reels to the website and remove reel videos that are
no longer needed (already posted or not in the queue). One website push per day at most, to save Vercel storage.
Only touches website/social/*.mp4 (root). Never touches social/web/ (used by /photos). Needs WEBSITE_TOKEN."""
import json, os, shutil, subprocess, sys, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
pend_path, queue_path = os.path.join(BASE, "pending.json"), os.path.join(BASE, "queue.json")
pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
queue = json.load(open(queue_path, encoding="utf-8"))
todo = [i for i in pend["items"] if i.get("publish") == "todo"]
keep = {os.path.basename(p["video"]) for p in queue["posts"] if not p.get("posted") and p.get("video")}

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
if not todo and not removed:
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
