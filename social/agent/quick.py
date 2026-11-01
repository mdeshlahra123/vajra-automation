"""Quick brain for Telegram /ask: one Gemini call with live data, answers in ~20-40 s.
Safe actions only (send media, pause/resume ads). Bigger jobs (new reel, queue moves, promote) are handed to agent.yml.
Env: GEMINI_API_KEY, META_ADS_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GH_TOKEN, TASK, WHO."""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
sys.path.insert(0, os.path.dirname(__file__))
import gem, tools

ROOT = tools.ROOT
task, who = os.environ.get("TASK", ""), os.environ.get("WHO", "")
t0 = time.time()
status = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "tools.py"), "status"],
                        capture_output=True, text=True, timeout=120).stdout
rules = open(os.path.join(ROOT, "GEMINI.md"), encoding="utf-8").read()
mem = open(os.path.join(ROOT, "agent", "memory.md"), encoding="utf-8").read()[-4000:]
prompt = f"""You are the VAJRA brain. Rules and context:
{rules}

Memory (latest):
{mem}

Live data right now (JSON):
{status[:14000]}

Posting slots: 09:30 IST = Trial Reel (non-followers first). 19:30 IST = the one main reel of the day (next "evening" reel), every day.
What REALLY posts next (computed exactly like the poster): {json.dumps({k: (v.get('id') + (' | ' + v.get('video', v.get('image', ''))) if isinstance(v, dict) else v) for k, v in tools.upcoming().items()}, ensure_ascii=False)}
IST now: {time.strftime('%Y-%m-%d %H:%M %A', time.gmtime(time.time() + 19800))}.

Request from {who or 'owner'} on Telegram: {task}

First understand what they actually asked.
If they ask to CHANGE a post but do not say what to change it to (e.g. "change tomorrow's post"), do NOT guess and do NOT act:
reply with what is planned now for that slot plus 3 numbered options (the next items of the same kind, one short line each), and ask "kaunsa lagaun? number bhejo".
Only act when they said which one (or replied to your options with a number). If they want a different TOPIC (not just order), say which items match. If it is a question, a complaint or a problem ("audio nahi aa raha", "kyu", "kaise"),
ANSWER IT directly using the System facts and live data. Do NOT just send a reel again. If it's a follow-up, the bracket at the start shows the bot message they replied to.

Answer as JSON only:
{{"reply": "1-6 short Hinglish lines that directly answer the question; real numbers from the data; no file names/IDs unless asked",
 "media": [{{"url": "reel .mp4 / image URL from the data", "caption": "short"}}],
 "actions": [["pause" or "resume", "<ad_id>"] or ["next", "<queue_id>"] or ["remember", "<owner preference to keep forever>"]],
 "deep": false}}
"media": ONLY when they ask to SEE a reel/post (e.g. "konsi reel jayegi", "dikhao"). For questions/complaints leave it [].
To change what posts in a slot: ["next", "<queue_id>"] makes that item the next one of its own kind (morning reel / evening reel / photo). Never use positions. Always add "remember" when the owner states a preference or rule.
NEVER say something is done unless you put the action for it in "actions". If you cannot do it yourself, say "main check karke batata hoon" and set deep.
Set "deep": true ONLY if the request needs a new reel, promoting a reel, or multi-step work, or a problem
you cannot explain from the facts (the bigger brain can read code and logs); then "reply" says what will happen.
Never break the hard rules (no spending, no budget changes)."""
try:
    out = gem.text("gemini-3.8-flash", prompt, json_mode=True)
except Exception as e:
    tools.tg("Jawab nahi bana (" + str(e)[:80] + "). Bada brain chala raha hun.")
    out = {"deep": True, "reply": ""}
print("gemini done in", round(time.time() - t0), "s:", json.dumps(out, ensure_ascii=False)[:600])
if out.get("reply"):
    tools.tg(out["reply"])
for m in (out.get("media") or [])[:3]:
    if m.get("url", "").startswith("https://"):
        tools.media(m["url"], m.get("caption", ""))
done = []
for act in out.get("actions") or []:
    if len(act) == 2 and act[0] == "next":
        try:
            tools.make_next(act[1]); done.append("queue")
        except BaseException as e:
            tools.tg(f"Queue badal nahi paya ({act[1]}): {str(e)[:80]}")
    elif len(act) == 2 and act[0] == "remember":
        open(os.path.join(ROOT, "agent", "memory.md"), "a", encoding="utf-8").write(f"\n- {time.strftime('%d %b')} ({who}): {act[1][:300]}"); done.append("memory")
    elif len(act) == 2 and act[0] in ("pause", "resume"):
        try:
            tools.ad(act[0], act[1]); tools.tg(f"Ad {act[0]} kar diya: {act[1]}")
        except Exception as e:
            tools.tg(f"Ad {act[0]} nahi hua: {str(e)[:80]}")
if "queue" in done:  # show the REAL new plan, computed like the poster, so nothing is claimed that did not happen
    u = tools.upcoming()
    m, e = u["morning"] or {}, (u["evening_tomorrow"] if u["after_1930_today"] else u["evening_today"]) or {}
    when_m = "Kal 09:30" if u["after_0930_today"] else "Aaj 09:30"; when_e = "Kal 19:30" if u["after_1930_today"] else "Aaj 19:30"
    tools.tg(f"✅ Queue check kiya (asli plan):\n{when_m}: {m.get('id', '-')}\n{when_e}: {e.get('id', '-')}")
    for it, cap in ((m, when_m), (e, when_e)):
        if it.get("video") or it.get("image"):
            tools.media(it.get("video") or it.get("image"), cap + " ko ye jayega")

if out.get("deep"):
    tools.dispatch("agent.yml", {"task": task[:900], "who": who})
print("total", round(time.time() - t0), "s")
