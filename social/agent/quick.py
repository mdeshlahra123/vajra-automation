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

Answer as JSON only:
{{"reply": "1-6 short Hinglish lines, real numbers from the data, no file names/IDs unless asked",
 "media": [{{"url": "reel .mp4 or image URL from the data, only if the answer is about specific reels/posts (max 3)", "caption": "short: kab post hoga / kya hai"}}],
 "actions": [["pause" or "resume", "<ad_id>"]],
 "deep": false}}
Set "deep": true ONLY if the request needs a new reel, moving the queue, promoting a reel, or multi-step work; then "reply" says what will happen.
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
for act in out.get("actions") or []:
    if len(act) == 2 and act[0] in ("pause", "resume"):
        try:
            tools.ad(act[0], act[1]); tools.tg(f"Ad {act[0]} kar diya: {act[1]}")
        except Exception as e:
            tools.tg(f"Ad {act[0]} nahi hua: {str(e)[:80]}")
if out.get("deep"):
    tools.dispatch("agent.yml", {"task": task[:900], "who": who})
print("total", round(time.time() - t0), "s")
