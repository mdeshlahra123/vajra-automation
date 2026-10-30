"""Turn a photo the owners sent on Telegram (social/inbox/*.jpg) into a usable library photo.
Gemini (free key) looks at it: describes it and rejects dirty/used sheets, people's faces up close, text/prices, blur.
OK photos are copied to assets/photos/in-<stamp>.jpg and listed in assets/photos/library.json {key: description},
which make_reel.py and story.py load, so new photos are used at once (fresh in the 21-day ledger).
  python social/engine/add_photo.py               process every inbox photo not processed yet
  python social/engine/add_photo.py --accept-all  owner-approved: add without the rejection check
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
INBOX = os.path.join(ROOT, "social", "inbox"); LIB = os.path.join(ROOT, "assets", "photos", "library.json")


def load():
    return json.load(open(LIB, encoding="utf-8")) if os.path.exists(LIB) else {}


def main():
    lib = load(); done = {v.get("src") for v in lib.values() if isinstance(v, dict)}
    for f in sorted(os.listdir(INBOX)) if os.path.isdir(INBOX) else []:
        if not f.lower().endswith((".jpg", ".jpeg", ".png")) or f in done:
            continue
        path = os.path.join(INBOX, f); ok, desc = True, "real site photo of VAJRA PP shuttering"
        try:
            import gem
            q = ("This photo was sent by the owners of VAJRA (grey PP hollow shuttering sheets) for Instagram reels/posts. "
                 "JSON only: {\"ok\": true/false, \"desc\": \"one line: what it shows (column/slab/beam/stock/cutting...)\", \"why\": \"\"}. "
                 "ok=false if: the sheet looks dirty/used/stained with old concrete, it is blurry or very dark, a price or readable text is "
                 "prominent, or a close-up face is the main subject.")
            r = gem.interact("gemini-3.5-flash-lite", [{"type": "text", "text": q}, gem.img_part(path)],
                             response_format={"type": "text", "mime_type": "application/json"})
            j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
            ok, desc = bool(j.get("ok")) or "--accept-all" in sys.argv, (j.get("desc") or desc)[:140]
            if not ok:
                desc += " | rejected: " + j.get("why", "")[:100]
        except Exception as e:
            print("check failed, adding anyway:", str(e)[:100])
        key = "in-" + f.split("-MrBeast")[0].split("-Rahul")[0].replace(".jpg", "")[:15].rstrip("-")
        if ok:
            shutil.copy(path, os.path.join(ROOT, "assets", "photos", key + ".jpg"))
        lib[key] = {"desc": "REAL owner photo: " + desc, "src": f, "ok": ok}
        print(("ADDED " if ok else "REJECTED ") + key, desc)
    json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def extra():
    """{key: description} of accepted library photos (for PHOTOS lists)."""
    return {k: v["desc"] for k, v in load().items() if isinstance(v, dict) and v.get("ok")}


if __name__ == "__main__":
    main()
