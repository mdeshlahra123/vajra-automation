"""VAJRA growth loop (owner, 6 Nov: 'completely autopilot'). Daily 18:00 IST via growth.yml, before the 19:30 post.
  1 MEASURE  : FB plays / watch / followers / comments + IG views / reach for every posted reel (perf history in social/perf.json)
  2 DIAGNOSE : each reel vs the median of the last 14; angle of every hook; tired angles; repeated hooks; winners
  3 DECIDE   : free LLM chain (Groq gpt-oss-120b -> Gemini free -> rules) picks the next angles, hooks to avoid,
               tonight's 19:30 reel, a winner to re-cut, and what real footage to ask the owners for
  4 ACT      : writes social/growth-plan.json (make_real.py reads it), retags/reorders the queue, re-cuts winners,
               refills the queue, asks owners (max every 3 days)
  5 REPORT   : Telegram ONLY when something changed + a Sunday weekly summary (owner: 'limited')
Never: spend money, change ad budgets, delete posted content, change any price.
  python social/growth.py [--dry]
"""
import datetime, json, os, re, subprocess, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "agent")); sys.path.insert(0, os.path.join(HERE, "engine")); sys.path.insert(0, HERE)
import tools, gem
DRY = "--dry" in sys.argv
P = lambda *a: os.path.join(HERE, *a)
load = lambda f, d: json.load(open(P(f), encoding="utf-8")) if os.path.exists(P(f)) else d
save = lambda f, o: json.dump(o, open(P(f), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
NOW = datetime.datetime.now(datetime.timezone.utc)
IST = NOW + datetime.timedelta(hours=5, minutes=30)
ANGLES = ["ply problem (breaks/swells/waste)", "money / repeat ply cost", "one man lifts / light", "wash and reuse",
          "smooth finish (column/slab)", "site use demo (column/beam/slab)", "contractor story / skit", "question / myth-buster",
          "before vs after", "offer / sample / call to action"]
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()
def sim(a, b):
    wa, wb = set(norm(a).split()), set(norm(b).split())
    return len(wa & wb) / max(1, len(wa | wb))


def measure():
    pt = tools.g(tools.PAGE, fields="access_token").get("access_token"); tok = {"access_token": pt} if pt else {}
    fb = []
    for v in tools.g(f"{tools.PAGE}/videos", fields="id,created_time,description,length", limit=30, **tok)["data"]:
        r = {"t": v["created_time"][:16], "hook": (v.get("description") or "").split("\n")[0][:90], "len": round(v.get("length") or 0)}
        for mt in ("fb_reels_total_plays", "post_video_avg_time_watched", "post_video_followers", "post_video_social_actions"):
            try:
                d = tools.g(f"{v['id']}/video_insights", metric=mt, **tok)["data"]
                if d: r[mt] = d[0]["values"][0]["value"]
            except Exception:
                pass
        if r.get("fb_reels_total_plays") is None:
            continue
        r["plays"] = r.pop("fb_reels_total_plays"); r["watch"] = round((r.pop("post_video_avg_time_watched", 0) or 0) / 1000, 1)
        r["foll"] = r.pop("post_video_followers", 0) or 0; r["com"] = (r.pop("post_video_social_actions", {}) or {}).get("COMMENT", 0)
        fb.append(r)
    ig_id = tools.g(tools.PAGE, fields="instagram_business_account")["instagram_business_account"]["id"]
    ig = {}
    for m in tools.g(f"{ig_id}/media", fields="id,timestamp,caption,media_product_type", limit=30)["data"]:
        if m.get("media_product_type") != "REELS":
            continue
        try:
            x = {i["name"]: i["values"][0]["value"] for i in tools.g(f"{m['id']}/insights", metric="reach,views")["data"]}
        except Exception:
            x = {}
        ig[norm((m.get("caption") or "").split("\n")[0])[:40]] = x
    followers = tools.g(ig_id, fields="followers_count").get("followers_count")
    for r in fb:
        r["ig_views"] = ig.get(norm(r["hook"])[:40], {}).get("views")
        r["age_h"] = round((NOW - datetime.datetime.fromisoformat(r["t"] + "+00:00")).total_seconds() / 3600)
    return fb, followers


def match_queue(fb):
    """attach queue id / ai flag / slot to each FB reel by caption hook."""
    q = json.load(open(P("queue.json"), encoding="utf-8"))
    posted = [p for p in q["posts"] + q.get("trials", []) if p.get("posted") and p.get("video")]
    for r in fb:
        best, s = None, 0.0
        for p in posted:
            try:
                h = open(os.path.join(HERE, p["caption"]), encoding="utf-8").read().split("\n")[0]
            except Exception:
                continue
            x = sim(h, r["hook"])
            if x > s: best, s = p, x
        if best and s >= 0.6:
            r.update(id=best["id"], ai=bool(best.get("ai")), slot=best.get("slot") or "morning")
    return q


def decide(table, pending, history, plan_old):
    ask = f"""You are the growth manager for VAJRA (PP shuttering sheets, Chhattisgarh) on Facebook/Instagram reels.
Main metric: Facebook plays at 48h+ (most reach), then followers gained, comments, watch seconds.
Allowed reel angles: {ANGLES}
Posted reels, newest first (age_h = hours since posting; judge only age_h >= 48):
{json.dumps(table, ensure_ascii=False)}
Pending reels in the queue (id, first caption line, ai): {json.dumps(pending, ensure_ascii=False)}
Last plan: {json.dumps(plan_old, ensure_ascii=False)[:600]}
Decide, returning JSON only:
{{"angles": {{"<hook of each posted reel>": "<one angle from the list>"}},
 "diagnosis": "2-3 short sentences: what is working, what is falling and why (specific)",
 "next_angles": ["3 angles for the next 3 new reels: best performer first, never the same angle as the last 2 posts, include 1 under-tried angle"],
 "avoid_hooks": ["first lines from the last 10 posts that new reels must not resemble"],
 "hook_ideas": ["5 fresh Hinglish hooks (max 9 words, sentence case, no price, no exact number of uses)"],
 "evening_pick": "id of the pending reel whose angle fits next_angles[0] best for 19:30 tonight, or null",
 "recut": "id of a posted reel with plays >= 2x the median, posted 10+ days ago, to re-cut with a new hook, or null",
 "ask_owners": "one short Hinglish request for specific REAL clips the library lacks for next_angles, or null"}}"""
    for fn in (lambda: gem.groq(ask, json_mode=True, model="openai/gpt-oss-120b"),
               lambda: gem.groq(ask, json_mode=True),
               lambda: gem.text("gemini-3.5-flash-lite", ask, json_mode=True)):
        try:
            d = fn()
            if isinstance(d, dict) and d.get("next_angles"):
                return d, "llm"
        except Exception as e:
            print("decide failed:", str(e)[:150])
    # rules fallback
    used = [r.get("angle") for r in table[:2]]
    return {"angles": {}, "diagnosis": "LLM unavailable; rules used.", "next_angles": [a for a in ANGLES if a not in used][:3],
            "avoid_hooks": [r["hook"] for r in table[:10]], "hook_ideas": [], "evening_pick": None, "recut": None, "ask_owners": None}, "rules"


def tg(text):
    if DRY:
        print("TG:", text); return
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                                 data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:3900]}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)


def main():
    st = load("growth-state.json", {"recut": {}, "asked": "", "weekly": ""})
    fb, followers = measure()
    q = match_queue(fb)
    perf = load("perf.json", {})
    for r in fb:
        perf[r["t"] + " " + r["hook"][:40]] = {**r, "seen": IST.strftime("%Y-%m-%d")}
    save("perf.json", dict(sorted(perf.items())[-120:]))
    mature = [r for r in fb if r["age_h"] >= 48]
    plays = sorted(r["plays"] for r in mature[:14]) or [0]
    median = plays[len(plays) // 2]
    table = [{k: r.get(k) for k in ("id", "hook", "age_h", "plays", "foll", "com", "watch", "ig_views", "ai", "slot")} for r in fb[:20]]
    for r in table:
        r["vs_median"] = round(r["plays"] / median, 2) if median and r["age_h"] >= 48 else None
    pend = [p for p in q["posts"] if not p.get("posted") and p.get("video")]
    pending = []
    for p in pend:
        try:
            pending.append({"id": p["id"], "hook": open(os.path.join(HERE, p["caption"]), encoding="utf-8").read().split("\n")[0][:90], "ai": bool(p.get("ai"))})
        except Exception:
            pass
    old = load("growth-plan.json", {})
    d, src = decide(table, pending, perf, old)
    changes = []
    # 1 plan for the reel builders
    plan = {"made": IST.strftime("%Y-%m-%d %H:%M"), "src": src, "next_angles": d.get("next_angles", [])[:3],
            "avoid_hooks": [h for h in (d.get("avoid_hooks") or [])][:12] or [r["hook"] for r in fb[:10]],
            "hook_ideas": (d.get("hook_ideas") or [])[:6], "diagnosis": d.get("diagnosis", ""), "median_plays": median}
    for r in fb[:10]:   # always include the real last 10 hooks
        if r["hook"] not in plan["avoid_hooks"]:
            plan["avoid_hooks"].append(r["hook"])
    if plan["next_angles"] != old.get("next_angles"):
        changes.append("Agli reels ka angle: " + " → ".join(plan["next_angles"]))
    if not DRY:
        save("growth-plan.json", plan)
    # 2 tonight's 19:30 pick (only before 19:00 IST, only a real pending reel whose file is live)
    ep = d.get("evening_pick")
    first_ev = next((p for p in pend if p.get("evening")), None)
    if ep and IST.hour < 19 and any(p["id"] == ep for p in pend) and (not first_ev or first_ev["id"] != ep):
        try:
            urllib.request.urlopen(urllib.request.Request(next(p for p in pend if p["id"] == ep)["video"], method="HEAD"), timeout=30)
            if not DRY:
                tools.set_evening(ep, True); tools.make_next(ep)
            changes.append(f"Aaj 19:30 ke liye {ep} chuni (angle fit)")
        except Exception as e:
            print("evening pick skipped:", e)
    # 3 re-cut a winner (max one every 3 days, each reel once)
    rc = d.get("recut")
    last_rc = max(st["recut"].values() or ["2000-01-01"])
    cand = next((r for r in mature if r.get("id") == rc), None)
    if not cand:   # rules: biggest winner 10+ days old, not yet re-cut
        cand = next((r for r in sorted(mature, key=lambda r: -r["plays"]) if r.get("id") and r["age_h"] >= 240
                     and r["plays"] >= 2 * median and r["id"] not in st["recut"]), None)
    if cand and cand.get("id") not in st["recut"] and (IST.date() - datetime.date.fromisoformat(last_rc)).days >= 3:
        src_mp4 = P("media", cand["id"] + ".mp4")
        if os.path.exists(src_mp4) and not DRY:
            note = (f"RECUT of a winning reel ({cand['plays']} FB plays). Keep the strongest moments but use a NEW hook (not: {cand['hook']}), "
                    f"new voice lines, different segment order. Angle: {plan['next_angles'][0] if plan['next_angles'] else ''}")
            cmd = [sys.executable, P("engine", "make_real.py"), "--files", "social/media/" + cand["id"] + ".mp4", "--note", note, "--who", "growth"]
            if cand.get("ai"): cmd.append("--ai")
            out = subprocess.run(cmd, capture_output=True, text=True); print(out.stdout[-800:], out.stderr[-800:])
            rid = next((l.split()[1] for l in out.stdout.splitlines() if l.startswith("REEL ")), None)
            if rid:
                import library_reel; library_reel.queue_or_send(rid)
                st["recut"][cand["id"]] = IST.strftime("%Y-%m-%d"); changes.append(f"Winner {cand['id']} ({cand['plays']} plays) ka naya cut bana: {rid}")
    # 4 keep the queue full
    if len(pend) < 3 and not DRY:
        out = subprocess.run([sys.executable, P("engine", "library_reel.py"), "--force"], capture_output=True, text=True)
        m = re.search(r"RECIPE (.+?) ->", out.stdout)
        if m: changes.append(f"Queue patli thi ({len(pend)} reels): nayi reel banai ({m.group(1)})")
    # 5 ask owners for real footage (max every 3 days)
    ao = d.get("ask_owners")
    if ao and (not st["asked"] or (IST.date() - datetime.date.fromisoformat(st["asked"])).days >= 3):
        tg("🎥 " + ao); st["asked"] = IST.strftime("%Y-%m-%d")
    # 6 report: only on change; weekly summary on Sunday
    if changes:
        tg("📈 Growth update\n" + (plan["diagnosis"] + "\n\n" if plan["diagnosis"] else "") + "\n".join("• " + c for c in changes))
    if IST.strftime("%A") == "Sunday" and st["weekly"] != IST.strftime("%Y-%m-%d"):
        wk = [r for r in fb if r["age_h"] <= 24 * 8]
        if wk:
            b, w = max(wk, key=lambda r: r["plays"]), min(wk, key=lambda r: r["plays"])
            tg(f"🗓 Hafte ki report\nReels: {len(wk)} | FB plays: {sum(r['plays'] for r in wk):,} | Naye FB followers (reels se): {sum(r['foll'] for r in wk)}\n"
               f"IG followers: {followers}\nBest: {b['hook'][:60]} ({b['plays']:,})\nWeak: {w['hook'][:60]} ({w['plays']:,})\n"
               f"Agle hafte: {' → '.join(plan['next_angles'])}")
        st["weekly"] = IST.strftime("%Y-%m-%d")
    if not DRY:
        save("growth-state.json", st)
    print(json.dumps({"src": src, "median": median, "changes": changes, "plan": plan}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
