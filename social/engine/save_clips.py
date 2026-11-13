"""Owner rule (30 Oct): clips sent on Telegram are only SAVED to the library, no reel is made right away.
Downloads each Telegram file_id to assets/clips/tg-<stamp>-<n>.mp4 and lists it in assets/clips/library.json
{name: {"who", "note", "flow": bool, "secs", "added"}}. library_reel.py later picks clips from the whole library.
  python social/engine/save_clips.py --clips id1,id2 --note "..." --who Name
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
LIB = os.path.join(ROOT, "assets", "clips", "library.json")


def load():
    return json.load(open(LIB, encoding="utf-8")) if os.path.exists(LIB) else {}


def main():
    from make_real import download
    from make_reel import dur
    ap = argparse.ArgumentParser(); ap.add_argument("--clips", required=True); ap.add_argument("--note", default=""); ap.add_argument("--who", default="")
    a = ap.parse_args()
    lib = load(); now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    stamp = now.strftime("%m%d-%H%M"); saved = []
    for i, fid in enumerate(x.strip() for x in a.clips.split(",") if x.strip()):
        name = f"tg-{stamp}-{i + 1}.mp4"; path = os.path.join(ROOT, "assets", "clips", name)
        download(fid, path)
        import ai_check  # owner 4 Nov: no caption needed, AI vs real is detected from the frames
        ai, desc = ai_check.check(path)
        ai = ai or "flow" in a.note.lower()
        lib[name] = {"who": a.who, "note": (a.note or ("AI: " if ai else "REAL: ") + desc)[:200], "flow": ai,
                     "secs": round(dur(path), 1), "added": now.strftime("%Y-%m-%d")}
        saved.append(name)
    json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SAVED", saved)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"n={len(saved)}\n")
        f.write(f"names={' '.join(saved)}\n")   # for skit_match.py


if __name__ == "__main__":
    main()
