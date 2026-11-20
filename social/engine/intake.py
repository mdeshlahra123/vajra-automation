"""Intake for reels made OUTSIDE this repo (Studio business engine, studio/engine/biz.py, 20 Nov).
Copies the reel into social/media, writes its caption (through caption_fix + claims), adds a pending item and pushes;
then GitHub sends the normal Telegram approval card (approve.yml mode=send). Approve/reject works exactly like any reel.
  python social/engine/intake.py --file X.mp4 --caption cap.txt --id 1120-1530 [--title ...] [--ai 1] [--cover c.jpg] [--no-push]"""
import argparse, json, os, shutil, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "social")); sys.path.insert(0, os.path.dirname(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--caption", required=True); ap.add_argument("--id", required=True)
    ap.add_argument("--title", default=""); ap.add_argument("--ai", default="0"); ap.add_argument("--cover", default="")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    rid = "reel-studio-" + a.id
    # never queue a reel without sound (owners, 27 Oct)
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.file, "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mx = float(o.split("max_volume:")[1].split("dB")[0]) if "max_volume:" in o else -99
    if mx < -60:
        sys.exit(f"intake: {rid} has no sound (max {mx} dB), not added")
    shutil.copy(a.file, os.path.join(ROOT, "social", "media", rid + ".mp4"))
    cap = open(a.caption, encoding="utf-8").read().strip()
    try:
        import claims; cap = claims.fix_caption(cap)
    except Exception as e:
        print("claims skipped:", e)
    try:
        import caption_fix; cap = caption_fix.fix(cap)
    except Exception as e:
        print("caption_fix skipped:", e)
    open(os.path.join(ROOT, "social", "captions", rid + ".txt"), "w", encoding="utf-8").write(cap + "\n")
    pp = os.path.join(ROOT, "social", "pending.json")
    pend = json.load(open(pp, encoding="utf-8")) if os.path.exists(pp) else {"items": []}
    pend["items"] = [i for i in pend["items"] if i["id"] != rid]
    ai = a.ai in ("1", "true", "True")
    pend["items"].append({"id": rid, "title": f"🎬 Studio reel (new engine): {a.title} | sound max {mx:.1f} dB\nStudio QC passed (format, loudness, voice, rules, frames).",
                          "file": f"social/media/{rid}.mp4", "caption": f"captions/{rid}.txt", "position": "alternate",
                          **({"ai": True} if ai else {"real": True}), "status": "draft", "by": "studio"})
    json.dump(pend, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("INTAKE", rid)
    if a.no_push:
        return
    g = lambda *x: subprocess.run(["git", "-C", ROOT, *x], check=True)
    g("add", f"social/media/{rid}.mp4", f"social/captions/{rid}.txt", "social/pending.json")
    g("commit", "-qm", f"studio intake {rid}")
    for _ in range(3):
        if subprocess.run(["git", "-C", ROOT, "pull", "-q", "--rebase"]).returncode == 0 and \
                subprocess.run(["git", "-C", ROOT, "push", "-q"]).returncode == 0:
            break
    else:
        sys.exit("intake: push failed")
    subprocess.run(["gh", "workflow", "run", "approve.yml", "-R", "mdeshlahra123/vajra-automation", "-f", "mode=send", "-f", f"id={rid}"], check=True)
    print("SENT FOR APPROVAL", rid)


if __name__ == "__main__":
    main()
