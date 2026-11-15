"""A2 worker on the Oracle server (systemd timer jb-vajragen, every 5 min). Outbound only, no open ports.

1. git pull the vajra-automation clone (~/vajra-automation, pushes with a repo-only deploy key)
2. if the reel queue is low: plan a new batch (social/engine/gen_plan.py, text via OmniRoute on this server)
3. generate up to 3 waiting clips on the Muse bridge (127.0.0.1:20240), each starting from its real VAJRA photo
4. save to assets/clips/gen/, add to assets/clips/library.json (AI), mark done in social/gen-jobs.json, push
   -> the push starts gen-build.yml on GitHub, which builds the reel when its batch is complete.
Daily Muse budget for VAJRA: VAJRA_VIDEO_CAP (default 9 of the bridge's 15).
  python3 social/server/vajra_gen.py          normal run
  python3 social/server/vajra_gen.py --once   one clip only (testing)
"""
import base64, datetime, json, os, subprocess, sys, time, urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
JOBS = os.path.join(REPO, "social", "gen-jobs.json")
LIB = os.path.join(REPO, "assets", "clips", "library.json")
BRIDGE = "http://127.0.0.1:20240"
KEY = open(os.path.expanduser("~/musebridge/key.txt")).read().strip()
CAP = int(os.environ.get("VAJRA_VIDEO_CAP", "9"))
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
LOG = os.path.expanduser("~/vajragen.log")


def log(*a):
    line = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def git(*a, check=True):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=check).stdout.strip()


def push(msg, paths):
    git("add", *paths)
    if subprocess.run(["git", "-C", REPO, "diff", "--cached", "--quiet"]).returncode == 0:
        return
    git("commit", "-qm", msg)
    for i in range(5):
        r = subprocess.run(["git", "-C", REPO, "pull", "--rebase", "-q"], capture_output=True, text=True)
        if r.returncode == 0 and subprocess.run(["git", "-C", REPO, "push", "-q"], capture_output=True).returncode == 0:
            return
        subprocess.run(["git", "-C", REPO, "rebase", "--abort"], capture_output=True)
        time.sleep(5 + 5 * i)
    raise RuntimeError("push failed: " + msg)


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def muse_video(prompt, image_path, size):
    body = {"prompt": prompt, "size": size}
    if image_path:
        body["image_b64"] = base64.b64encode(open(os.path.join(REPO, image_path), "rb").read()).decode()
    req = urllib.request.Request(BRIDGE + "/v1/videos", method="POST", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=660))["file"]


def health():
    try:
        return json.load(urllib.request.urlopen(BRIDGE + "/health", timeout=15))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    git("pull", "--rebase", "-q", check=False)
    # plan more reels when the queue is low (text through OmniRoute on this server)
    r = subprocess.run([sys.executable, os.path.join(REPO, "social", "engine", "gen_plan.py")], capture_output=True, text=True, cwd=REPO)
    out = (r.stdout + r.stderr).strip().splitlines()
    if any(l.startswith("PLANNED") for l in out):
        log(*[l for l in out if l.startswith("PLANNED")]); push("gen: new batch planned (server)", ["social/gen-jobs.json"])
    elif r.returncode:
        log("plan error:", " | ".join(out[-3:]))
    jb = load(JOBS, {"jobs": [], "batches": {}})
    today = datetime.datetime.now(IST).date().isoformat()
    used = sum(1 for j in jb["jobs"] if (j.get("done_at") or "").startswith(today) and j.get("kind") == "video")
    todo = [j for j in jb["jobs"] if j["status"] == "todo" and jb["batches"].get(j["batch"], {}).get("status") == "waiting"]
    if not todo:
        return
    h = health()
    if not h.get("ok") or not h.get("loggedIn", True):
        log("muse not ready:", h); return
    left = min(CAP - used, h["caps"]["video"] - h["usage"]["video"] if h.get("usage", {}).get("day") == today else CAP)
    for j in todo[: max(0, min(3, left)) if "--once" not in sys.argv else 1]:
        t = time.time()
        try:
            src = muse_video(j["prompt"], j.get("start_image"), j.get("size", "9:16"))
            dst = os.path.join(REPO, j["out"]); os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            jb = load(JOBS, jb)   # reload: a pull may have changed it
            jj = next(x for x in jb["jobs"] if x["id"] == j["id"])
            jj.update(status="done", done_at=datetime.datetime.now(IST).isoformat(timespec="minutes"), secs=round(time.time() - t))
            lib = load(LIB, {})
            lib[os.path.relpath(dst, os.path.join(REPO, "assets", "clips")).replace("\\", "/")] = {
                "who": "muse", "note": "AI (Muse): " + j["prompt"][170:330], "flow": True, "secs": 10.0,
                "added": today, "gen": j["batch"]}
            json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            push(f"gen: clip {j['id']} (Muse)", [j["out"], "social/gen-jobs.json", "assets/clips/library.json"])
            log("clip ok", j["id"], f"{round(time.time() - t)} s")
        except Exception as e:
            jb = load(JOBS, jb); jj = next(x for x in jb["jobs"] if x["id"] == j["id"])
            jj["tries"] = jj.get("tries", 0) + 1; jj["error"] = str(e)[:200]
            if jj["tries"] >= 3:
                jj["status"] = "failed"; jb["batches"][j["batch"]]["status"] = "failed"
            json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            push(f"gen: clip {j['id']} failed (try {jj['tries']})", ["social/gen-jobs.json"])
            log("clip FAILED", j["id"], str(e)[:200]); break


if __name__ == "__main__":
    main()
