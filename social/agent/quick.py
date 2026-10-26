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

Reels post 09:30 IST and images 19:30 IST, one per day each, in queue order (first = next). IST now: {time.strftime('%Y-%m-%d %H:%M', time.gmtime(time.time() + 19800))}.

Request from {who or 'owner'} on Telegram: {task}

First understand what they actually asked. If it is a question, a complaint or a problem ("audio nahi aa raha", "kyu", "kaise"),
ANSWER IT directly using the System facts and live data. Do NOT just send a reel again. If it's a follow-up, the bracket at the start shows the bot message they replied to.

Answer as JSON only:
{{"reply": "1-6 short Hinglish lines that directly answer the question; real numbers from the data; no file names/IDs unless asked",
 "media": [{{"url": "reel .mp4 / image URL from the data", "caption": "short"}}],
 "actions": [["pause" or "resume", "<ad_id>"] or ["move", "<queue_id>", <new position, 0 = next>] or ["remember", "<owner preference to keep forever>"]],
 "deep": false}}
"media": ONLY when they ask to SEE a reel/post (e.g. "konsi reel jayegi", "dikhao"). For questions/complaints leave it [].
To change what posts next/tonight: use "move" (e.g. move tonight's image to a later position, which brings the next one forward). Always add "remember" when the owner states a preference or rule.
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
    if len(act) == 3 and act[0] == "move":
        try:
            tools.move(act[1], int(act[2])); done.append("queue")
        except BaseException as e:
            tools.tg(f"Queue badal nahi paya ({act[1]}): {str(e)[:80]}")
    elif len(act) == 2 and act[0] == "remember":
        open(os.path.join(ROOT, "agent", "memory.md"), "a", encoding="utf-8").write(f"\n- {time.strftime('%d %b')} ({who}): {act[1][:300]}"); done.append("memory")
    elif len(act) == 2 and act[0] in ("pause", "resume"):
        try:
            tools.ad(act[0], act[1]); tools.tg(f"Ad {act[0]} kar diya: {act[1]}")
        except Exception as e:
            tools.tg(f"Ad {act[0]} nahi hua: {str(e)[:80]}")
if "queue" in done:  # show the owner the real new order, so nothing is claimed that did not happen
    q = json.load(open(os.path.join(ROOT, "social", "queue.json"), encoding="utf-8"))
    pend = [p for p in q["posts"] if not p.get("posted")]
    nr = next((p for p in pend if p.get("video")), {}); ni = next((p for p in pend if not p.get("video")), {})
    tools.tg(f"✅ Queue badal di. Agli reel (09:30): {nr.get('id', '-')}\nAgli post (19:30): {ni.get('id', '-')}")
    if ni.get("image"):
        tools.media(ni["image"], "Ab ye jayegi 19:30 ko")
if out.get("deep"):
    tools.dispatch("agent.yml", {"task": task[:900], "who": who})
print("total", round(time.time() - t0), "s")
