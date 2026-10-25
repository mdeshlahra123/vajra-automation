"""Tools for the VAJRA brain (Gemini CLI agent). See GEMINI.md.
Env: META_ADS_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GH_TOKEN (GitHub token for workflow dispatch)."""
import json, os, subprocess, sys, urllib.parse, urllib.request

if os.path.exists("/tmp/vajra-secrets.json"):
    for _k, _v in json.load(open("/tmp/vajra-secrets.json")).items():
        os.environ.setdefault(_k, _v)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = "https://graph.facebook.com/v24.0/"
ACCOUNT, PAGE = "act_1417609487254050", "1296793536861294"


def g(path, **p):
    p["access_token"] = os.environ["META_ADS_TOKEN"]
    return json.load(urllib.request.urlopen(V + path + "?" + urllib.parse.urlencode(p), timeout=60))


def leads(row):
    return sum(float(a["value"]) for a in row.get("actions", []) if a["action_type"] in ("lead", "onsite_conversion.messaging_conversation_started_7d"))


def status():
    out = {}
    try:
        ig = g(PAGE, fields="instagram_business_account")["instagram_business_account"]["id"]
        acc = g(ig, fields="followers_count,media_count")
        out["instagram"] = {"followers": acc.get("followers_count")}
        posts = []
        for m in g(f"{ig}/media", fields="id,timestamp,media_product_type,like_count,comments_count,caption", limit=12)["data"]:
            row = {"date": m["timestamp"][:10], "type": m.get("media_product_type"), "likes": m.get("like_count"),
                   "comments": m.get("comments_count"), "hook": (m.get("caption") or "").split("\n")[0][:70]}
            try:
                ins = g(f"{m['id']}/insights", metric="reach,saved,shares,views")["data"]
                row.update({x["name"]: x["values"][0]["value"] for x in ins})
            except Exception:
                pass
            posts.append(row)
        out["recent_posts"] = posts
        for p, m in zip(posts, g(f"{ig}/media", fields="id", limit=12)["data"]):
            p["media_id"] = m["id"]
    except Exception as e:
        out["instagram_error"] = str(e)[:200]
    try:
        ads = {a["id"]: a for a in g(f"{ACCOUNT}/ads", fields="name,effective_status", limit=100)["data"]}
        ins = {x["ad_id"]: x for x in g(f"{ACCOUNT}/insights", level="ad", date_preset="last_7d", fields="ad_id,spend,actions,ctr", limit=100).get("data", [])}
        out["ads_last_7d"] = [{"id": i, "name": a["name"], "status": a["effective_status"],
                               "spend": float(ins.get(i, {}).get("spend", 0)), "leads": leads(ins.get(i, {})),
                               "ctr": float(ins.get(i, {}).get("ctr", 0))} for i, a in ads.items() if a["effective_status"] in ("ACTIVE", "PAUSED")]
        out["ad_balance"] = g(ACCOUNT, fields="funding_source_details").get("funding_source_details", {}).get("display_string")
    except Exception as e:
        out["ads_error"] = str(e)[:200]
    try:
        import datetime
        tk = os.environ["META_ADS_TOKEN"]
        d = g("debug_token", input_token=tk)["data"]
        exp = d.get("data_access_expires_at") or 0
        days = (datetime.datetime.utcfromtimestamp(exp) - datetime.datetime.utcnow()).days if exp else None
        out["meta_token"] = {"valid": d.get("is_valid"), "data_access_days_left": days,
                             "ACTION": "WARN OWNERS: Mehul must log in again to Meta (Business Suite / the app) before data access ends, or posting and ads tools stop"
                             if (days is not None and days < 21) or not d.get("is_valid") else None}
    except Exception as e:
        out["meta_token_error"] = str(e)[:150]
    q = json.load(open(os.path.join(ROOT, "social", "queue.json"), encoding="utf-8"))
    pend = [p for p in q["posts"] if not p.get("posted")]
    out["queue"] = {"pending_reels_in_order_next_first_9:30": [(p["id"], p["video"]) for p in pend if p.get("video")],
                    "pending_images_in_order_next_first_19:30": [(p["id"], p.get("image")) for p in pend if not p.get("video")],
                    "last_posted": [(p["id"], p["posted"]) for p in q["posts"] if p.get("posted")][-5:]}
    pf = os.path.join(ROOT, "social", "pending.json")
    if os.path.exists(pf):
        out["waiting_for_approval"] = [i["id"] for i in json.load(open(pf, encoding="utf-8"))["items"] if i.get("status") == "sent"]
    print(json.dumps(out, ensure_ascii=False, indent=1))


def ad(action, ad_id):
    if action not in ("pause", "resume"):
        sys.exit("only pause/resume allowed")
    req = urllib.request.Request(V + ad_id, data=urllib.parse.urlencode(
        {"status": "PAUSED" if action == "pause" else "ACTIVE", "access_token": os.environ["META_ADS_TOKEN"]}).encode())
    print(json.load(urllib.request.urlopen(req, timeout=60)))


def promote(media_id, name):
    """Turn an organic Instagram reel into a lead ad in the existing ad set (same budget, no extra spend). Max 6 active ads."""
    ads = g(f"{ACCOUNT}/ads", fields="effective_status", limit=100)["data"]
    if sum(a["effective_status"] == "ACTIVE" for a in ads) >= 6:
        sys.exit("already 6 active ads; pause a weak one first")
    def post(path, d):
        d["access_token"] = os.environ["META_ADS_TOKEN"]
        return json.load(urllib.request.urlopen(urllib.request.Request(V + path, data=urllib.parse.urlencode(d).encode()), timeout=60))
    c = post(f"{ACCOUNT}/adcreatives", {"name": name, "source_instagram_media_id": media_id, "instagram_user_id": "17841424780649708",
             "object_id": PAGE, "call_to_action": json.dumps({"type": "SIGN_UP", "value": {"lead_gen_form_id": "4528850134099610",
             "link": "https://vajraformwork.vercel.app/"}})})
    a = post(f"{ACCOUNT}/ads", {"name": name, "adset_id": "120251450839500600", "creative": json.dumps({"creative_id": c["id"]}), "status": "ACTIVE"})
    print("new ad", a)


def dispatch(workflow, inputs):
    req = urllib.request.Request(f"https://api.github.com/repos/mdeshlahra123/vajra-automation/actions/workflows/{workflow}/dispatches",
                                 data=json.dumps({"ref": "main", "inputs": inputs}).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"})
    urllib.request.urlopen(req, timeout=30); print("started", workflow)


def reel(brief):
    q = json.load(open(os.path.join(ROOT, "social", "queue.json"), encoding="utf-8"))
    n = sum(1 for p in q["posts"] if not p.get("posted") and p.get("video"))
    if n >= 6:
        sys.exit(f"queue already has {n} pending reels; not making another (limit 6)")
    dispatch("make-reel.yml", {"brief": brief[:400], "res": "720p"})


def move(qid, pos):
    path = os.path.join(ROOT, "social", "queue.json")
    q = json.load(open(path, encoding="utf-8"))
    it = next((p for p in q["posts"] if p["id"] == qid and not p.get("posted")), None)
    if not it:
        sys.exit("pending item not found")
    q["posts"].remove(it)
    pend_idx = [i for i, p in enumerate(q["posts"]) if not p.get("posted")]
    at = pend_idx[int(pos)] if int(pos) < len(pend_idx) else len(q["posts"])
    q["posts"].insert(at, it)
    json.dump(q, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2); print("moved", qid, "to", pos)


def tg(text):
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                                 data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": "🧠 " + text[:3800]}).encode(),
                                 headers={"Content-Type": "application/json"})
    print(json.load(urllib.request.urlopen(req, timeout=30)).get("ok"))


def media(url, caption):
    """Send the actual video/photo to Telegram by URL; falls back to a text link."""
    m, f = ("sendVideo", "video") if url.lower().split("?")[0].endswith(".mp4") else ("sendPhoto", "photo")
    import time  # Telegram caches files per exact URL; a daily tag makes it fetch the current version
    url += ("&" if "?" in url else "?") + "v=" + time.strftime("%Y%m%d")
    if m == "sendVideo":
        caption += "\n🔊 Awaaz ke liye video kholo / tap karo"
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{m}",
                                     data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], f: url, "caption": "🧠 " + caption[:1000]}).encode(),
                                     headers={"Content-Type": "application/json"})
        print(json.load(urllib.request.urlopen(req, timeout=60)).get("ok"))
    except Exception as e:
        print("media failed, sending link:", str(e)[:100]); tg(caption + "\n" + url)
if __name__ == "__main__":
    a = sys.argv[1:]
    {"status": lambda: status(), "ad": lambda: ad(a[1], a[2]), "reel": lambda: reel(" ".join(a[1:])),
     "move": lambda: move(a[1], a[2]), "promote": lambda: promote(a[1], " ".join(a[2:])),
     "leads": lambda: subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "leads_report.py")]), "tg": lambda: tg(" ".join(a[1:])),
     "media": lambda: media(a[1], " ".join(a[2:]))}.get(a[0] if a else "", lambda: sys.exit(__doc__))()
