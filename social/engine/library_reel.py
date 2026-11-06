"""Make ONE reel from the whole clip library (owner, 30 Oct) and put it in the queue.
Picks 2-3 real clips that were not used in the last 21 days (usage ledger), newest first, and makes a
real-footage reel with make_real.py (voice, music, end card, delivery reviewer). If the reviewer passes,
it goes straight into the queue (evening slot) and the owners get it on Telegram as FYI; if the reviewer
flags it, it is sent for an Approve/Reject tap instead.
Runs when fewer than 4 reels are pending (library-reel.yml, daily) or by hand.
  python social/engine/library_reel.py [--force]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "social"))
import usage
CLIPS = os.path.join(ROOT, "assets", "clips")
SKIP_END = {"beam-box-3.mp4"}  # ends on a dirty sheet; fine to use but planner is told


def pending_reels():
    q = json.load(open(os.path.join(ROOT, "social", "queue.json"), encoding="utf-8"))
    return sum(1 for p in q["posts"] if p.get("video") and not p.get("posted"))


def library():
    lib = {}
    try:
        lib = json.load(open(os.path.join(CLIPS, "library.json"), encoding="utf-8"))
    except Exception:
        pass
    names = [f for f in os.listdir(CLIPS) if f.endswith(".mp4")]
    return names, lib


# Reel recipes (owner, 4 Nov): any mix of AI/real clips and photos. Slots in story order:
# (kind, source, count)  kind: clip|photo   source: ai|real   ; reveal=True adds 2 real VAJRA photos at the end.
RECIPES = [
    ("full AI clips", [("clip", "ai", 3)], "AI story start to end: pain, then VAJRA sheet answer", False),
    ("AI clips then real clips", [("clip", "ai", 2), ("clip", "real", 2)], "AI pain first, then the real site answer", False),
    ("real clips then AI clips", [("clip", "real", 2), ("clip", "ai", 2)], "real site hook first, then AI story/explainer", False),
    ("full AI photos", [("photo", "ai", 4)], "AI image slideshow: pain, then VAJRA answer", False),
    ("full real photos", [("photo", "real", 4)], "real photo slideshow: site, sheet, finish", False),
    ("AI photos then real photos", [("photo", "ai", 2), ("photo", "real", 2)], "AI pain images, then real VAJRA photos", False),
    ("real clips + AI photos", [("clip", "real", 2), ("photo", "ai", 2)], "real site clips, AI images to explain the point", False),
    ("AI clips + real photos", [("clip", "ai", 2)], "AI pain clips, then real VAJRA photos as the answer", True),
    ("real clips + real photos", [("clip", "real", 2), ("photo", "real", 2)], "real site clips with real finish photos", False),
    ("full real clips", [("clip", "real", 3)], "real site footage only", False),
    ("real photo hook + AI clips", [("photo", "real", 1), ("clip", "ai", 2)], "real finished result first as hook, then AI story", False),
    ("AI clip + real clip + AI photo", [("clip", "ai", 1), ("clip", "real", 1), ("photo", "ai", 1)], "AI hook, real proof, AI closing image", False),
    ("AI photos then real clips", [("photo", "ai", 2), ("clip", "real", 2)], "AI pain images, then real site answer", False),
    ("real photos then AI clips", [("photo", "real", 2), ("clip", "ai", 2)], "real VAJRA photos, then AI story", False),
]
STATE = os.path.join(ROOT, "social", "recipe-state.json")


def photo_pools():
    import make_reel
    plib = {}
    try:
        plib = json.load(open(os.path.join(ROOT, "assets", "photos", "library.json"), encoding="utf-8"))
    except Exception:
        pass
    ok = lambda k: os.path.exists(os.path.join(ROOT, "assets", "photos", k + ".jpg"))
    ai = [k for k, v in plib.items() if isinstance(v, dict) and v.get("ok") and v.get("ai") and ok(k)]
    real = [k for k in make_reel.PHOTOS if ok(k) and k not in ai]
    return {"ai": ai, "real": real}


def fill(recipe, pools):
    """item paths for a recipe, freshest first; None if the library can't fill it."""
    taken, files = set(), []
    for kind, src, n in recipe[1]:
        pool = [x for x in pools[(kind, src)] if x not in taken]
        fr = usage.fresh(pool) or []
        if len(fr) < n:   # nothing fresh enough: least recently used is fine for photos only
            fr = fr + sorted([x for x in pool if x not in fr], key=lambda k: -usage.age(k)) if kind == "photo" else fr
        if len(fr) < n:
            return None
        pick = fr[:n]; taken.update(pick)
        files += [("assets/clips/" + x) if kind == "clip" else ("assets/photos/" + x + ".jpg") for x in pick]
    return files


def main():
    if pending_reels() >= 4 and "--force" not in sys.argv:
        print("enough reels pending; nothing to do"); return
    names, lib = library()
    added = lambda n: lib.get(n, {}).get("added", "2026-10-28")
    clips = sorted(names, key=added, reverse=True)
    pp = photo_pools()
    pools = {("clip", "ai"): [n for n in clips if lib.get(n, {}).get("flow")], ("clip", "real"): [n for n in clips if not lib.get(n, {}).get("flow")],
             ("photo", "ai"): pp["ai"], ("photo", "real"): pp["real"]}
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    want = next((r for r in RECIPES if r[0] == os.environ.get("RECIPE")), None)
    order = [want] if want else sorted(RECIPES, key=lambda r: st.get(r[0], ""))   # least recently used recipe first
    for r in order:
        files = fill(r, pools)
        if files:
            break
        print("skip recipe (library can't fill):", r[0])
    else:
        print("no recipe can be filled from fresh items"); return
    pick = [os.path.basename(f) for f in files]
    note = f"recipe: {r[0]}. items: " + "; ".join(lib.get(n, {}).get("note", n) for n in pick)[:300]
    print("RECIPE", r[0], "->", pick)
    cmd = [sys.executable, os.path.join(HERE, "make_real.py"), "--files", ",".join(files), "--note", note, "--who", "library",
           "--order", r[2] + " (keep the items in the given order)"] + (["--reveal"] if r[3] else [])
    out = subprocess.run(cmd, capture_output=True, text=True)
    pick = [p[:-4] if p.endswith(".jpg") else p for p in pick]   # ledger keys: clip file names, photo keys
    st[r[0]] = __import__("datetime").date.today().isoformat()
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    print(out.stdout[-2000:], out.stderr[-1500:])
    rid = next((l.split()[1] for l in out.stdout.splitlines() if l.startswith("REEL ")), None)
    if not rid:
        raise SystemExit("reel not made")
    usage.mark(*pick)
    queue_or_send(rid)


def queue_or_send(rid):
    """reviewer ✅ -> straight into the queue (evening slot) + FYI; ⚠️ -> Telegram approval card."""
    import tg
    pend = json.load(open(os.path.join(ROOT, "social", "pending.json"), encoding="utf-8"))
    it = next(i for i in pend["items"] if i["id"] == rid)
    if "✅" in it.get("title", ""):   # reviewer passed: straight into the queue, evening slot
        it["status"] = "approved"; it["by"] = "auto (reviewer ok)"; tg.add_to_queue(it)
        q = json.load(open(os.path.join(ROOT, "social", "queue.json"), encoding="utf-8"))
        for p in q["posts"]:
            if p["id"] == rid:
                p["evening"] = True
        json.dump(q, open(os.path.join(ROOT, "social", "queue.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(pend, open(os.path.join(ROOT, "social", "pending.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        tg.call("sendMessage", chat_id=tg.CHAT, text=f"🎬 Library se nayi reel bani aur queue mein daal di (reviewer ✅): {rid}. Pasand na ho to 'hatao {rid}' likho.")
        print("QUEUED", rid)
    else:
        tg.send(rid); print("SENT FOR APPROVAL", rid)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"id={rid}\n")


if __name__ == "__main__":
    main()
