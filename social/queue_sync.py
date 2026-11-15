"""A1 (MASTER-PLAN): the content queue on /admin, with no GitHub token on the website.

The website (api/admin.js) only talks to the Orders Google Sheet:
  - it READS a snapshot of the queue from the hidden tab "_queue_view" (JSON split over A1:A20)
  - it WRITES commands as rows in the hidden tab "_queue_cmds": [time, cmd, id, status, note]
This script (GitHub: queue-sync.yml every 10 min, and inside post.yml right before posting) applies pending
commands to social/queue.json, then writes a fresh snapshot. The schedule logic matches daily-post.ps1:
  09:30 trial = trials pool first, else the next non-evening reel, else any reel
  19:30 main  = the next evening-tagged reel, else any reel, else a photo
Commands: up / down (swap with the neighbour in the same lane), tonight (next 19:30, pinned), morning (next 09:30
trial), evening / noevening (move between lanes), hold, unhold.
  python social/queue_sync.py            apply + snapshot (writes queue.json if changed)
  python social/queue_sync.py --dry      show what would change, write nothing
Env: SHEETS_TOKEN (GitHub secret) or ./sheets-token.json.
"""
import datetime, json, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(BASE)
QUEUE = os.path.join(BASE, "queue.json")
SHEET = "1O2AqihNecxMMJ6hfqXhrAVP2JcOWN5dI8GlAAZliwSY"
VIEW, CMDS = "_queue_view", "_queue_cmds"
DRY = "--dry" in sys.argv
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


# ---------- Google Sheets over plain HTTPS (no pip needed on the runner) ----------
def token():
    t = json.loads(os.environ.get("SHEETS_TOKEN") or open(os.path.join(ROOT, "sheets-token.json"), encoding="utf-8").read())
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": t["refresh_token"],
                                   "client_id": t["client_id"], "client_secret": t["client_secret"]}).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=30))["access_token"]


TOK = None


def api(path, method="GET", body=None):
    global TOK
    TOK = TOK or token()
    req = urllib.request.Request(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def ensure_tabs():
    tabs = {s["properties"]["title"] for s in api("?fields=sheets.properties.title")["sheets"]}
    add = [{"addSheet": {"properties": {"title": t, "hidden": True}}} for t in (VIEW, CMDS) if t not in tabs]
    if add:
        api(":batchUpdate", "POST", {"requests": add})
        api(f"/values/{urllib.parse.quote(CMDS + '!A1:E1')}?valueInputOption=RAW", "PUT",
            {"values": [["time", "cmd", "id", "status", "note"]]})


# ---------- queue logic ----------
def pending(lst):
    return [p for p in lst if not p.get("posted")]


def lane(p, q):
    if p in q.get("trials", []):
        return "trial"
    if not p.get("video"):
        return "photo"
    return "evening" if p.get("evening") else "morning"


def find(q, pid):
    for k in ("posts", "trials", "hold"):
        for p in q.get(k, []):
            if p.get("id") == pid and not p.get("posted"):
                return k, p
    return None, None


def apply(q, cmd, pid):
    where, p = find(q, pid)
    if not p:
        return "not found (posted or removed)"
    lst = q[where]
    if cmd in ("up", "down"):
        if where == "hold":
            return "on hold"
        ln = lane(p, q)
        same = [x for x in pending(lst) if lane(x, q) == ln]
        i = same.index(p); j = i - 1 if cmd == "up" else i + 1
        if not 0 <= j < len(same):
            return "already at the " + ("top" if cmd == "up" else "end")
        a, b = lst.index(p), lst.index(same[j])
        lst[a], lst[b] = lst[b], lst[a]
        return "ok"
    if cmd == "tonight":
        if not p.get("video"):
            return "only reels post at 19:30"
        lst.remove(p); p["evening"] = True; p["pin"] = True
        for x in q["posts"]:
            if x is not p and not x.get("posted"):
                x.pop("pin", None)
        firsts = [n for n, x in enumerate(q["posts"]) if not x.get("posted") and x.get("video") and x.get("evening")]
        q["posts"].insert(firsts[0] if firsts else len(q["posts"]), p)
        return "ok"
    if cmd == "morning":
        if not p.get("video"):
            return "only reels post at 09:30"
        lst.remove(p); p.pop("evening", None); p.pop("pin", None)
        q.setdefault("trials", []).insert(0, p)   # 09:30 is always a trial reel; the trials pool goes first
        return "ok"
    if cmd in ("evening", "noevening"):
        if where != "posts" or not p.get("video"):
            return "only queued reels"
        if cmd == "evening": p["evening"] = True
        else: p.pop("evening", None); p.pop("pin", None)
        return "ok"
    if cmd == "hold":
        if where == "hold":
            return "already on hold"
        lst.remove(p); p.pop("pin", None); q.setdefault("hold", []).append(p)
        return "ok"
    if cmd == "unhold":
        if where != "hold":
            return "not on hold"
        lst.remove(p); q["posts"].append(p)
        return "ok"
    return "unknown command"


def hook(p):
    try:
        return open(os.path.join(BASE, p["caption"]), encoding="utf-8").read().strip()[:600]
    except Exception:
        return ""


def card(p, q):
    return {"id": p["id"], "kind": "reel" if p.get("video") else ("carousel" if p.get("slides") else "photo"),
            "lane": lane(p, q), "video": p.get("video") or p.get("reel") or "", "image": p.get("image") or ((p.get("slides") or [""])[0]),
            "cover": p.get("cover") or "", "ai": bool(p.get("ai")), "pin": bool(p.get("pin")), "caption": hook(p)}


def schedule(q, days=7):
    """Same picking rules as daily-post.ps1 (and publish_site.py next.json)."""
    now = datetime.datetime.now(IST)
    trials = [p for p in pending(q.get("trials", [])) if p.get("video")]
    am = [p for p in pending(q["posts"]) if p.get("video") and not p.get("evening")]
    ev = [p for p in pending(q["posts"]) if p.get("video") and p.get("evening")]
    photos = [p for p in pending(q["posts"]) if not p.get("video")]
    posted_today = {p.get("slot") or "morning" for p in q["posts"] + q.get("trials", []) if str(p.get("posted")) == now.date().isoformat()}
    out = []
    for n in range(days):
        d = now.date() + datetime.timedelta(days=n)
        for t, slot in (("09:30", "morning"), ("19:30", "evening")):
            if n == 0 and (slot in posted_today or now.strftime("%H:%M") > t):
                continue   # already done today
            if slot == "morning":
                p = trials.pop(0) if trials else (am.pop(0) if am else (ev.pop(0) if ev else None))
            else:
                p = ev.pop(0) if ev else (am.pop(0) if am else (photos.pop(0) if photos else None))
            out.append({"date": d.isoformat(), "time": t, "slot": slot, "id": p["id"] if p else None})
    return out


def snapshot(q):
    items = {}
    for p in pending(q["posts"]) + pending(q.get("trials", [])) + q.get("hold", []):
        c = card(p, q); c["held"] = p in q.get("hold", []); items[p["id"]] = c
    lanes = {ln: [p["id"] for p in pending(q["posts"]) + pending(q.get("trials", [])) if lane(p, q) == ln]
             for ln in ("trial", "morning", "evening", "photo")}
    return {"updated": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M"), "schedule": schedule(q),
            "lanes": lanes, "hold": [p["id"] for p in q.get("hold", [])], "items": items}


def main():
    ensure_tabs()
    rows = api(f"/values/{urllib.parse.quote(CMDS + '!A2:E500')}").get("values", [])
    q = json.load(open(QUEUE, encoding="utf-8"))
    results = []
    for n, r in enumerate(rows, 2):
        r = r + [""] * (5 - len(r))
        if r[3] != "pending":
            continue
        res = apply(q, r[1].strip(), r[2].strip())
        results.append((n, "done" if res == "ok" else "error", res))
        print(f"row {n}: {r[1]} {r[2]} -> {res}")
    changed = bool(results) and any(s == "done" for _, s, _ in results)
    if DRY:
        print(json.dumps(snapshot(q), ensure_ascii=False)[:1500]); return
    if changed:
        with open(QUEUE, "w", encoding="utf-8", newline="\n") as f:   # no BOM, same layout as before
            f.write(json.dumps(q, ensure_ascii=False, indent=2))
    data = [{"range": f"{CMDS}!D{n}:E{n}", "values": [[s, note]]} for n, s, note in results]
    blob = json.dumps(snapshot(q), ensure_ascii=False)
    chunks = [blob[i:i + 45000] for i in range(0, len(blob), 45000)][:20]
    data.append({"range": f"{VIEW}!A1:A20", "values": [[c] for c in chunks] + [[""]] * (20 - len(chunks))})
    api("/values:batchUpdate", "POST", {"valueInputOption": "RAW", "data": data})
    print("snapshot written:", len(blob), "chars;", "queue.json changed" if changed else "queue.json unchanged")
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"changed={'1' if changed else ''}\n")


if __name__ == "__main__":
    main()
