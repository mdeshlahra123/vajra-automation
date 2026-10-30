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


def main():
    if pending_reels() >= 4 and "--force" not in sys.argv:
        print("enough reels pending; nothing to do"); return
    names, lib = library()
    real = [n for n in names if not lib.get(n, {}).get("flow")]
    flow = [n for n in names if lib.get(n, {}).get("flow")]
    added = lambda n: lib.get(n, {}).get("added", "2026-10-28")
    fresh_flow = sorted(usage.fresh(flow), key=added, reverse=True)
    if len(fresh_flow) >= 2:   # AI problem clips first, then real VAJRA ending (make_real adds it)
        pick, note = fresh_flow[:2], "flow"
    else:
        fr = sorted(usage.fresh(real), key=added, reverse=True)
        if len(fr) < 2:
            print("not enough fresh clips (need 2 not used in 21 days):", fr); return
        pick, note = fr[:3], "library clips: " + "; ".join(lib.get(n, {}).get("note", n) for n in fr[:3])[:300]
    files = ",".join("assets/clips/" + n for n in pick)
    print("making reel from", pick)
    out = subprocess.run([sys.executable, os.path.join(HERE, "make_real.py"), "--files", files, "--note", note, "--who", "library"],
                         capture_output=True, text=True)
    print(out.stdout[-2000:], out.stderr[-1500:])
    rid = next((l.split()[1] for l in out.stdout.splitlines() if l.startswith("REEL ")), None)
    if not rid:
        raise SystemExit("reel not made")
    usage.mark(*pick)
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
