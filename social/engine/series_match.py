"""Clips for a 'Shuttering Ki Duniya' episode: the owner writes the code (S12) in a caption of the batch.
save_clips.py stores that caption as the note of every clip in the batch, in send order.
Clips are added to the open episode in order; when it has all its parts -> make_skit.py builds it (parts + voiced end card).
Prints SERIES_IDS=... and writes series_ids=<id id> to GITHUB_OUTPUT. Tagged clips are skipped by skit_match / library_reel.
  python social/engine/series_match.py tg-1114-1010-1.mp4 tg-1114-1010-2.mp4 ...
"""
import datetime, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STATE = os.path.join(ROOT, "social", "series-state.json")
LIB = os.path.join(ROOT, "assets", "clips", "library.json")


def main(names):
    if not os.path.exists(STATE):
        print("no series state"); return
    st = json.load(open(STATE, encoding="utf-8")); lib = json.load(open(LIB, encoding="utf-8"))
    built = []
    for n in names:
        m = re.search(r"\bS(\d+)\b", lib.get(n, {}).get("note") or "", re.I)
        if not m:
            continue
        code = "S" + m.group(1); ep = st.get("open", {}).get(code)
        if not ep or ep.get("built"):
            print(n, "-> code", code, "not open"); continue
        if n in ep["clips"]:
            continue
        lib.setdefault(n, {})["series"] = code; lib[n]["skit"] = code
        if float(lib[n].get("secs") or 0) >= ep["n"] * 8 * 0.75:   # one long video made with Flow Extend = whole episode
            ep["clips"] = [n]; ep["whole"] = True
            print(n, "->", code, "whole episode in one video"); continue
        if not ep.get("whole") and len(ep["clips"]) < ep["n"]:
            ep["clips"].append(n)
            print(n, "->", code, f"part {len(ep['clips'])}/{ep['n']}")
    json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for code, ep in st.get("open", {}).items():
        if ep.get("built") or (len(ep["clips"]) < ep["n"] and not ep.get("whole")):
            continue
        files = ",".join(os.path.join("assets", "clips", c) for c in ep["clips"])
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_skit.py"), "--files", files,
                            "--title", f"Shuttering Ki Duniya {code}: {ep['title']}", "--hook", ep.get("hook", "")],
                           capture_output=True, text=True)
        print(r.stdout[-800:], r.stderr[-800:])
        sid = [l.split("=", 1)[1] for l in r.stdout.splitlines() if l.startswith("SKIT_ID=")]
        if r.returncode == 0 and sid:
            ep["built"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"); ep["id"] = sid[-1]; built.append(sid[-1])
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SERIES_IDS=" + " ".join(built))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"series_ids={' '.join(built)}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
