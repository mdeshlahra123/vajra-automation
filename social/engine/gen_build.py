"""A2 builder (GitHub, gen-build.yml): turns a finished Muse batch into a queued VAJRA reel.

For each batch in social/gen-jobs.json with status "waiting" whose clips are all done:
  make_skit.py --files <clips> --subs <spoken lines> (blurred 9:16 fill, captions, voiced end card, AI label, audio check)
  -> quality gate: 2 frames per clip checked by a vision model against the VAJRA look rules
  -> library_reel.queue_or_send: passes go straight into the queue (19:30 line); fails get "CHECK:" and go to Telegram
Failed batches (a clip failed 3 times) are reported once on Telegram.
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
JOBS = os.path.join(ROOT, "social", "gen-jobs.json")
PEND = os.path.join(ROOT, "social", "pending.json")

GATE = """These frames come from a short Instagram reel for VAJRA (plain light-grey hollow plastic shuttering sheets).
Frames {probs} are from the PROBLEM clip (should show old BROWN wooden plywood). The other frames show the VAJRA answer.
Fail the reel if ANY of these is clearly true: a grey/white plastic sheet appears in the problem frames; brown plywood
is presented as the VAJRA sheet; garbled or readable text/logos printed on the grey sheets; badly deformed hands, faces or
bodies; the scene is unsafe (no helmet is fine) or not an Indian construction/warehouse setting.
JSON only: {{"ok": true/false, "issues": "short reason or empty"}}"""


def frames(path, n, work, tag):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip() or 10)
    out = []
    for k, t in enumerate([d * (k + 1) / (n + 1) for k in range(n)]):
        f = os.path.join(work, f"{tag}{k}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=-2:480", f])
        if os.path.exists(f):
            out.append(f)
    return out


def gate(clips):
    """(ok, note). If no vision model answers, the reel is not auto-queued."""
    import gem
    work = tempfile.mkdtemp(); imgs = []
    for i, c in enumerate(clips):
        imgs += frames(os.path.join(ROOT, c), 2, work, f"c{i}")
    probs = "1-2"
    inp = [{"type": "text", "text": GATE.format(probs=probs)}]
    for k, f in enumerate(imgs):
        inp += [{"type": "text", "text": f"Frame {k + 1}:"}, gem.img_part(f)]
    try:
        r = gem.interact("gemini-3.5-flash-lite", inp, response_format={"type": "text", "mime_type": "application/json"})
        j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
        return bool(j.get("ok")), (j.get("issues") or "")[:150]
    except Exception as e:
        return False, "auto-check could not run (" + str(e)[:60] + ")"


def tg(text):
    import urllib.request
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok and chat:
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": text}).encode(), headers={"Content-Type": "application/json"}), timeout=30)


def main():
    jb = json.load(open(JOBS, encoding="utf-8"))
    built = []
    for bid, b in jb["batches"].items():
        jobs = [j for j in jb["jobs"] if j["batch"] == bid]
        if b.get("status") == "failed" and not b.get("reported"):
            tg(f"⚠️ Muse reel {bid} nahi bani: ek clip 3 baar fail hua ({next((j.get('error','') for j in jobs if j['status']=='failed'), '')[:120]}). Agla batch apne aap banega.")
            b["reported"] = True
        if b.get("status") != "waiting" or not jobs or any(j["status"] != "done" for j in jobs):
            continue
        clips = [j["out"] for j in sorted(jobs, key=lambda j: j["id"])]
        if not all(os.path.exists(os.path.join(ROOT, c)) for c in clips):
            print(bid, "clips not in checkout yet"); continue
        rid = "reel-" + bid
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_skit.py"), "--files", ",".join(clips), "--id", rid,
                            "--title", b.get("hook") or b.get("title", bid), "--hook", b.get("hook", ""), "--subs", json.dumps(b.get("lines", []), ensure_ascii=False)],
                           capture_output=True, text=True)
        print(r.stdout[-600:], r.stderr[-600:])
        if r.returncode != 0:
            b["status"] = "build-failed"; b["error"] = (r.stdout + r.stderr)[-300:]
            tg(f"⚠️ Muse reel {bid} build fail hua: {b['error'][-150:]}"); continue
        ok, note = gate(clips)
        pend = json.load(open(PEND, encoding="utf-8"))
        it = next(i for i in pend["items"] if i["id"] == rid)
        it["title"] = (f"🎬 Muse reel: {b.get('title')} · ✅ auto-check" if ok else f"CHECK: {note} · Muse reel: {b.get('title')}")
        json.dump(pend, open(PEND, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        b["status"] = "built"; b["reel"] = rid; b["gate"] = "ok" if ok else note
        json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        import library_reel
        library_reel.queue_or_send(rid)
        built.append(rid)
    json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("BUILT", built)


if __name__ == "__main__":
    main()
