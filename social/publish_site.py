"""Once a day (before the reel post): copy approved engine reels to the website and remove reel videos that are
no longer needed (already posted or not in the queue). One website push per day at most, to save Vercel storage.
Only touches website/social/*.mp4 (root). Never touches social/web/ (used by /photos). Needs WEBSITE_TOKEN."""
import json, os, shutil, subprocess, sys, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
pend_path, queue_path = os.path.join(BASE, "pending.json"), os.path.join(BASE, "queue.json")
pend = json.load(open(pend_path, encoding="utf-8")) if os.path.exists(pend_path) else {"items": []}
queue = json.load(open(queue_path, encoding="utf-8"))
todo = [i for i in pend["items"] if i.get("publish") == "todo"]
keep = {"msg-sample.jpg", "msg-offer.jpg"}  # messenger auto-reply photo; # every file a not-yet-posted item still needs (video, image, cover, slides), incl. held reels and scheduled stories
for p in queue["posts"] + queue.get("hold", []) + queue.get("stories", []) + queue.get("trials", []):
    if p.get("posted"):
        continue
    for k in ("video", "image", "cover", "reel"):
        if p.get(k):
            keep.add(os.path.basename(p[k]))
    keep.update(os.path.basename(s) for s in p.get("slides", []))
for i in pend["items"]:  # reels waiting for approval keep their covers
    if i.get("status") in ("sent", "draft") and i.get("cover"):
        keep.add(os.path.basename(i["cover"]))

url = f"https://x-access-token:{os.environ['WEBSITE_TOKEN']}@github.com/mdeshlahra123/vajraformwork.git"
subprocess.run(["git", "clone", "-q", "--depth", "1", url, "site"], check=True)
sdir = os.path.join("site", "social")
for i in todo:
    shutil.copy(os.path.join(BASE, "..", i["file"]), os.path.join(sdir, os.path.basename(i["file"])))
    i["publish"] = "done"
# 4 Nov safety net: ANY unposted queue/trial reel whose video is ours but missing on the site gets uploaded,
# however it was approved (tap, chat, brain, library). Files come from social/media.
for p in queue["posts"] + queue.get("trials", []):
    v = p.get("video") or ""
    if p.get("posted") or "vajraformwork.vercel.app/social/" not in v:
        continue
    f = os.path.basename(v); src = os.path.join(BASE, "media", f)
    if not os.path.exists(os.path.join(sdir, f)) and os.path.exists(src):
        shutil.copy(src, os.path.join(sdir, f)); todo.append({"id": p["id"], "file": "social/media/" + f})
        print("safety net: uploaded missing", f)
        for i in pend["items"]:
            if i["id"] == p["id"]:
                i["publish"] = "done"
removed = [f for f in os.listdir(sdir) if f.endswith((".mp4", ".jpg")) and f not in keep and not any(os.path.basename(i["file"]) == f for i in todo)]
for f in removed:
    os.remove(os.path.join(sdir, f))
print("add:", [i["id"] for i in todo], "| remove:", removed)
# brand-style grid covers for queued reels that don't have one yet (needs ffmpeg)
import re, shutil as _sh
if _sh.which("ffmpeg") and os.environ.get("GEMINI_API_KEY"):  # Gemini picks the frame (cover.smart)
    sys.path.insert(0, os.path.join(BASE, "engine")); import cover
    for p in queue["posts"]:
        if p.get("posted") or not p.get("video") or p.get("cover"):
            continue
        f = os.path.join(sdir, os.path.basename(p["video"]))
        if not os.path.exists(f):
            continue
        try:
            name = os.path.basename(f).replace(".mp4", "-cover.jpg")
            note = cover.smart(f, open(os.path.join(BASE, p["caption"]), encoding="utf-8").read(), os.path.join(sdir, name))
            p["cover"] = "https://vajraformwork.vercel.app/social/" + name; removed.append("cover:" + name)
            # (owner, 2 Nov: don't send the cover thumbnail to Telegram — not needed)
        except Exception as e:
            print("cover failed", p["id"], e)
    json.dump(queue, open(queue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# Fallback cover (2 Nov): any queued reel still without a cover gets a plain ffmpeg frame, even when Gemini is
# rate-limited or GEMINI_API_KEY is missing. Also copies a cover whose file exists locally but isn't on the site.
if _sh.which("ffmpeg"):
    changed = False
    for p in queue["posts"]:
        if p.get("posted") or not p.get("video"):
            continue
        name = os.path.basename(p["video"]).replace(".mp4", "-cover.jpg")
        dst = os.path.join(sdir, name)
        if not p.get("cover"):   # no cover at all -> grab a frame ~1s in
            vf = os.path.join(sdir, os.path.basename(p["video"]))
            if os.path.exists(vf):
                try:
                    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "1", "-i", vf,
                                    "-frames:v", "1", "-q:v", "3", dst], check=True, timeout=60)
                    p["cover"] = "https://vajraformwork.vercel.app/social/" + name
                    keep.add(name); changed = True; print("fallback cover:", name)
                except Exception as e:
                    print("fallback cover failed", p["id"], e)
        elif not os.path.exists(dst):   # cover set but file missing on site -> copy it from the engine media dir
            src = os.path.join(BASE, "media", name)
            if os.path.exists(src):
                shutil.copy(src, dst); keep.add(name); print("copied cover:", name)
    if changed:
        json.dump(queue, open(queue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
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
# same rules as daily-post.ps1 (1 Nov): 09:30 = trial reel (trial pool first, else next non-evening reel),
# 19:30 = main reel (next evening-tagged reel, else any reel), photo only when no reel is left.
trials = [p for p in queue.get("trials", []) if not p.get("posted") and p.get("video")]
am = [p for p in pend_posts if p.get("video") and not p.get("evening")]
ev = [p for p in pend_posts if p.get("video") and p.get("evening")]
for n in range(7):
    d = str(today + datetime.timedelta(days=n))
    m = trials.pop(0) if trials else (am.pop(0) if am else (ev.pop(0) if ev else None))
    e = ev.pop(0) if ev else (am.pop(0) if am else None)
    for p, t in ((m, "09:30 trial"), (e, "19:30")):
        if p:
            nxt["reels"].append({"date": d, "time": t, "id": p["id"], "url": p["video"], "hook": hook(p)})
for n, p in enumerate([p for p in pend_posts if p.get("image")][:7]):
    nxt["images"].append({"date": "when no reel is left", "time": "19:30", "id": p["id"], "url": p["image"], "hook": hook(p)})
npath = os.path.join(sdir, "next.json")
old = open(npath, encoding="utf-8").read() if os.path.exists(npath) else ""
new = json.dumps(nxt, ensure_ascii=False, indent=1)
if new != old:
    open(npath, "w", encoding="utf-8").write(new)
g = lambda *a: subprocess.run(["git", "-C", "site", *a], check=True)
g("config", "user.name", "vajra-bot"); g("config", "user.email", "vajra-bot@users.noreply.github.com")
g("add", "-A", "social")
# commit only if something actually changed (covers, reels, removals, next.json)
if subprocess.run(["git", "-C", "site", "diff", "--cached", "--quiet"]).returncode != 0:
    g("commit", "-q", "-m", f"bot: daily reels +{len(todo)} -{len(removed)}"); g("push", "-q")
json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# wait until the newest added reel is live, so today's post can fetch it
for i in todo[-1:]:
    u = "https://vajraformwork.vercel.app/social/" + os.path.basename(i["file"])
    for _ in range(30):
        try:
            urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=20); print("live:", u); break
        except Exception:
            time.sleep(10)

# Guard (owners, 27 Oct): never post a reel without sound. Any silent pending reel is moved to queue "hold".
if _sh.which("ffmpeg"):
    q = json.load(open(queue_path, encoding="utf-8")); moved = []
    for p in [p for p in q["posts"] if not p.get("posted") and p.get("video")][:3]:
        try:
            r = subprocess.run(["ffmpeg", "-hide_banner", "-i", p["video"], "-vn", "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True, timeout=180).stderr
            mx = float(r.split("max_volume:")[1].split("dB")[0]) if "max_volume:" in r else -99
        except Exception:
            continue
        if mx < -60:
            q["posts"].remove(p); q.setdefault("hold", []).append(p); moved.append(p["id"])
    if moved:
        json.dump(q, open(queue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        try:
            subprocess.run(["curl", "-s", "-X", "POST", f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                            "-d", f"chat_id={os.environ['TELEGRAM_CHAT_ID']}", "--data-urlencode",
                            "text=🔇 In reels mein awaaz nahi thi, post nahi kiya (hold pe daal diya): " + ", ".join(moved)], timeout=30)
        except Exception:
            pass
