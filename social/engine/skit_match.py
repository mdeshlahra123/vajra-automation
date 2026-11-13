"""Is a newly saved clip one of the 3 parts of today's skit? No caption needed (owner rule, 4 Nov).

skit_prompts.py stores the skit it sent as "open" in social/skit-prompts-state.json (valid 3 days).
After save_clips.py saves a batch, this looks at 3 frames of each new clip and asks Gemini (free key) which of the
3 skit prompts it matches (or none). Matches are stored in the open skit. When parts 1, 2 and 3 are all matched
(in one batch or over several), it builds the reel with make_skit.py --files (parts in story order + end card)
and sends it for approval. Unmatched clips stay normal library clips.
Caption "skit" on a clip forces it to count as a skit part (order from the frames, else the order sent).
  python social/engine/skit_match.py tg-1113-1200-1.mp4 tg-1113-1200-2.mp4 ...
"""
import datetime, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
STATE = os.path.join(ROOT, "social", "skit-prompts-state.json")
LIB = os.path.join(ROOT, "assets", "clips", "library.json")

Q = """These frames come from ONE short video clip. Below are the 3 parts of a dialogue skit prompt that the owner may have
turned into videos in Google Flow. Which part does this clip show? Judge by the people, what they hold or do, the material
(brown plywood vs grey plastic sheet), the setting and the mood. If it clearly fits none of them, answer 0.
Part 1: {p1}
Part 2: {p2}
Part 3: {p3}
JSON only: {{"part": 0|1|2|3, "sure": true/false, "why": "short"}}"""


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def match(path, parts, forced=False):
    import gem, ai_check
    work = tempfile.mkdtemp()
    imgs = ai_check.frames(path, work)
    r = gem.interact("gemini-3.5-flash-lite",
                     [{"type": "text", "text": Q.format(p1=parts[0], p2=parts[1], p3=parts[2])}] + [gem.img_part(x) for x in imgs],
                     response_format={"type": "text", "mime_type": "application/json"})
    j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
    part = int(j.get("part") or 0)
    if part and not j.get("sure", True) and not forced:
        part = 0   # unsure -> keep as normal library clip
    return part, (j.get("why") or "")[:120]


def main(names):
    st = load(STATE, {})
    sk = st.get("open")
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    if not sk or (sk.get("built") and not ORDER):   # manual --order may rebuild
        print("no open skit"); return
    if (now.date() - datetime.date.fromisoformat(sk["sent"])).days > 3:
        print("open skit older than 3 days, ignored"); return
    lib = load(LIB, {})
    got = sk.setdefault("clips", {})          # "1"/"2"/"3" -> clip file name
    if ORDER:   # manual: these clips ARE parts 1,2,3 in this order
        got.clear(); got.update({str(i + 1): n for i, n in enumerate(ORDER[:3])})
        for n in ORDER[:3]:
            lib.setdefault(n, {})["skit"] = sk["angle"]
        names = []
    hits = []                                 # (clip, part) for skit clips in this batch, in the order sent
    names = [n for n in names if not lib.get(n, {}).get("series")]   # series_match.py owns these
    for n in names:
        forced = "skit" in (lib.get(n, {}).get("note") or "").lower()
        try:
            part, why = match(os.path.join(ROOT, "assets", "clips", n), sk["parts"], forced)
        except Exception as e:
            print("match failed", n, str(e)[:120]); continue
        print(n, "-> part", part, why)
        if part or forced:
            hits.append([n, part])
    # 13 Nov live test: Flow kept the same 2 people in part 1 and 2, Gemini called both "part 1".
    # If parts in one batch collide (or are missing), the owner sent them in order: give the free parts by send order.
    free = [str(i) for i in (1, 2, 3) if str(i) not in got]
    parts_seen = [p for _, p in hits if p]
    if hits and (len(set(parts_seen)) < len(parts_seen) or len(parts_seen) < len(hits)) and len(hits) <= len(free):
        print("parts collide/unsure in this batch -> using send order", free[:len(hits)])
        for h, p in zip(hits, free):
            h[1] = int(p)
    for n, part in hits:
        if part and str(part) not in got:
            got[str(part)] = n
            lib.setdefault(n, {})["skit"] = sk["angle"]   # library_reel skips skit parts
    json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if all(str(i) in got for i in (1, 2, 3)):
        files = ",".join(os.path.join("assets", "clips", got[str(i)]) for i in (1, 2, 3))
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_skit.py"), "--files", files, "--title", sk["angle"]],
                           capture_output=True, text=True)
        print(r.stdout[-1500:], r.stderr[-1500:])
        if r.returncode == 0:
            sk["built"] = now.strftime("%Y-%m-%d %H:%M")
            sid = [l for l in r.stdout.splitlines() if l.startswith("SKIT_ID=")]
            if sid:
                sk["id"] = sid[-1].split("=", 1)[1]
                with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
                    f.write(f"skit_id={sk['id']}\n")
    else:
        print("skit parts so far:", got)
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


ORDER = []

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--order":   # skit_match.py --order a.mp4,b.mp4,c.mp4  (manual: parts 1,2,3)
        ORDER = [x.strip() for x in args[1].split(",") if x.strip()]
        args = []
    main(args)
