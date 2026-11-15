"""A2 worker on the Oracle server (systemd timer jb-vajragen, every 5 min). Outbound only, no open ports.

1. git pull ~/vajra-automation (read only, public https clone) and ~/vajra-gen (the drop repo, pushes with a
   deploy key that only works for MehulDeshlahra/vajra-gen)
2. if the reel queue is low: plan a new batch (social/engine/gen_plan.py, text via OmniRoute on this server)
3. generate up to 3 waiting clips on the Muse bridge (127.0.0.1:20240), each starting from its real VAJRA photo
4. save to ~/vajra-gen/clips/, mark done in ~/vajra-gen/gen-jobs.json, push
   -> gen-build.yml in vajra-automation (every 15 min) builds the reel once its batch is complete.
Daily Muse budget for VAJRA: VAJRA_VIDEO_CAP (default 13 of the bridge's 15) shared by reels and episodes.
  python3 social/server/vajra_gen.py          normal run
  python3 social/server/vajra_gen.py --once   one clip only (testing)
"""
import base64, datetime, json, os, subprocess, sys, time, urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # vajra-automation
DROP = os.path.expanduser(os.environ.get("VAJRA_DROP", "~/vajra-gen"))
JOBS = os.path.join(DROP, "gen-jobs.json")
BRIDGE = "http://127.0.0.1:20240"
KEY = open(os.path.expanduser("~/musebridge/key.txt")).read().strip()
CAP = int(os.environ.get("VAJRA_VIDEO_CAP", "13"))
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
LOG = os.path.expanduser("~/vajragen.log")


def log(*a):
    line = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def git(*a, check=True, repo=None):
    return subprocess.run(["git", "-C", repo or DROP, *a], capture_output=True, text=True, check=check).stdout.strip()


def push(msg, paths):
    git("add", *paths)
    if subprocess.run(["git", "-C", DROP, "diff", "--cached", "--quiet"]).returncode == 0:
        return
    git("commit", "-qm", msg)
    for i in range(5):
        r = subprocess.run(["git", "-C", DROP, "pull", "--rebase", "-q"], capture_output=True, text=True)
        if r.returncode == 0 and subprocess.run(["git", "-C", DROP, "push", "-q"], capture_output=True).returncode == 0:
            return
        subprocess.run(["git", "-C", DROP, "rebase", "--abort"], capture_output=True)
        time.sleep(5 + 5 * i)
    raise RuntimeError("push failed: " + msg)


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def start_path(ref, jb):
    """'@<job id>' = the output of an earlier job in the drop repo (A3 episode reference image); else a repo photo."""
    if ref and ref.startswith("@"):
        dep = next((x for x in jb["jobs"] if x["id"] == ref[1:]), None)
        return os.path.join(DROP, dep["out"]) if dep and dep.get("status") == "done" else None
    return os.path.join(REPO, ref) if ref else ""


def muse_image(prompt, size):
    req = urllib.request.Request(BRIDGE + "/v1/images/generations", method="POST",
                                 data=json.dumps({"prompt": prompt, "size": size}).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=420))["data"][0]["file"]


def muse_video(prompt, image_path, size):
    body = {"prompt": prompt, "size": size}
    if image_path:
        body["image_b64"] = base64.b64encode(open(image_path, "rb").read()).decode()
    req = urllib.request.Request(BRIDGE + "/v1/videos", method="POST", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=660))["file"]


def finish(jb, bid):
    """A4: when every clip of a batch is done, check it with OmniRoute vision and write the caption on this server.
    Saved on the batch as "gate" and "caption"; gen_build.py on GitHub uses them (and checks itself only if missing)."""
    b = jb["batches"].get(bid, {})
    vids = sorted((x for x in jb["jobs"] if x["batch"] == bid and x.get("kind", "video") == "video"), key=lambda x: x["id"])
    if "gate" in b or not vids or any(x["status"] != "done" for x in vids):
        return
    sys.path.insert(0, os.path.join(REPO, "social", "engine"))
    try:
        import gen_build, make_skit
        series = b.get("kind") == "series"
        ok, note = gen_build.gate([os.path.join(DROP, x["out"]) for x in vids], "series" if series else "reel")
        if not note.startswith("auto-check could not run"):
            b["gate"] = {"ok": ok, "issues": note, "by": "server"}
        title = f"Shuttering Ki Duniya: {b.get('title')}. {b.get('hook', '')}" if series else (b.get("hook") or b.get("title", bid))
        cap = make_skit.caption(title, b.get("hook", "")).rsplit("\n\n" + make_skit.TAGS, 1)[0].strip()
        if cap:
            b["caption"] = cap
        log("checked", bid, "ok" if ok else "FAIL", note[:100])
    except Exception as e:
        log("check error", bid, str(e)[:200])


def health():
    try:
        return json.load(urllib.request.urlopen(BRIDGE + "/health", timeout=15))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    # read-only copy: always match GitHub exactly (a shallow sparse clone can't "pull" after history moves)
    git("fetch", "-q", "--depth", "1", "origin", "main", check=False, repo=REPO)
    git("reset", "-q", "--hard", "origin/main", check=False, repo=REPO)
    git("pull", "--rebase", "-q", check=False)
    # plan more reels when the queue is low (text through OmniRoute on this server)
    r = subprocess.run([sys.executable, os.path.join(REPO, "social", "engine", "gen_plan.py")], capture_output=True, text=True, cwd=REPO,
                       env={**os.environ, "GEN_JOBS": JOBS})
    out = (r.stdout + r.stderr).strip().splitlines()
    if any(l.startswith("PLANNED") for l in out):
        log(*[l for l in out if l.startswith("PLANNED")]); push("gen: new batch planned (server)", ["gen-jobs.json"])
    elif r.returncode:
        log("plan error:", " | ".join(out[-3:]))
    jb = load(JOBS, {"jobs": [], "batches": {}})
    today = datetime.datetime.now(IST).date().isoformat()
    used = sum(1 for j in jb["jobs"] if (j.get("done_at") or "").startswith(today) and j.get("kind") == "video")
    todo = [j for j in jb["jobs"] if j["status"] == "todo" and jb["batches"].get(j["batch"], {}).get("status") == "waiting"]
    # a clip that starts from an episode image waits until that image exists (images come first in the list)
    if not todo:
        return
    h = health()
    if not h.get("ok") or not h.get("loggedIn", True):
        log("muse not ready:", h); return
    left = min(CAP - used, h["caps"]["video"] - h["usage"]["video"] if h.get("usage", {}).get("day") == today else CAP)
    n = 0
    for j in todo:
        if n >= (1 if "--once" in sys.argv else 4) or (j.get("kind") == "video" and left <= 0):
            break
        t = time.time()
        try:
            if j.get("kind") == "image":
                src = muse_image(j["prompt"], j.get("size", "9:16"))
            else:
                img = start_path(j.get("start_image"), load(JOBS, jb))
                if img is None:
                    continue   # its reference image is not ready yet
                src = muse_video(j["prompt"], img, j.get("size", "9:16")); left -= 1
            n += 1
            ext = os.path.splitext(src)[1] or ".mp4"
            dst = os.path.join(DROP, "clips", j["id"] + ext); os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            jb = load(JOBS, jb)   # reload: a pull may have changed it
            jj = next(x for x in jb["jobs"] if x["id"] == j["id"])
            jj.update(status="done", done_at=datetime.datetime.now(IST).isoformat(timespec="minutes"), secs=round(time.time() - t),
                      out="clips/" + j["id"] + ext)
            finish(jb, j["batch"])   # last clip of the batch -> quality check + caption here, in the same push
            json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            push(f"gen: {j.get('kind', 'video')} {j['id']} (Muse)", ["clips/" + j["id"] + ext, "gen-jobs.json"])
            log("clip ok", j["id"], f"{round(time.time() - t)} s")
        except Exception as e:
            jb = load(JOBS, jb); jj = next(x for x in jb["jobs"] if x["id"] == j["id"])
            jj["tries"] = jj.get("tries", 0) + 1; jj["error"] = str(e)[:200]
            if jj["tries"] >= 3:
                jj["status"] = "failed"; jb["batches"][j["batch"]]["status"] = "failed"
            json.dump(jb, open(JOBS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            push(f"gen: clip {j['id']} failed (try {jj['tries']})", ["gen-jobs.json"])
            log("clip FAILED", j["id"], str(e)[:200]); break


if __name__ == "__main__":
    main()
