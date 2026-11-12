"""Sales helpers on Facebook Messenger (owner, 1 Nov). Runs after messenger_reply.py every ~10 min.
1. HOT LEAD alert: customer message with a phone number, a quantity or buying words -> Telegram, once per message.
2. ONE follow-up: offer sent, customer silent, their last message 18-22 h old (inside Meta's 24 h window) -> one nudge.
3. Daily CALL LIST: first run after 09:00 IST -> Telegram list of customers who wrote in the last 24 h (local first).
State: social/leads-state.json.   python social/leads_bot.py [--dry]
Env: META_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import datetime, json, os, re, sys, urllib.parse, urllib.request
BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "leads-state.json")
PAGE, V = "1296793536861294", "https://graph.facebook.com/v24.0"
OFFER_MARK = "VAJRA PP shuttering sheet"
FOLLOW = ("Namaste ji 🙏 Kal aapne VAJRA PP sheet ke baare mein poocha tha.\n"
          "Aap kis shehar se hain? Rate, delivery aur ₹199 sample ki poori jaankari de dete hain.\n"
          "📞 Call/WhatsApp: 83050 70160")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
QTY = re.compile(r"\b\d+\s*(?:pis|pish|pees|piece|pieces|pcs|pc|sheet|sheets|seet|shit|nag|पीस|शीट)\b", re.I)
BUY = re.compile(r"order|chahiye|chaiye|chahie|bhejo|bhej do|bhejiye|address|upi|payment|kab tak|delivery|"
                 r"चाहिए|भेजो|भेज|ऑर्डर|आर्डर|पेमेंट", re.I)
LOCAL = re.compile(r"raipur|durg|bhilai|रायपुर|दुर्ग|भिलाई", re.I)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get(path, **p):
    return json.load(urllib.request.urlopen(f"{V}/{path}?" + urllib.parse.urlencode(p), timeout=60))
def post(path, tok, body):
    req = urllib.request.Request(f"{V}/{path}?access_token={tok}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))
def tg(text, dry):
    if dry:
        print("TG>>", text); return
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                                 data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:3900]}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)

def main():
    dry = "--dry" in sys.argv
    pt = get(PAGE, fields="access_token", access_token=os.environ["META_TOKEN"])["access_token"]
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    hot, fu = set(st.get("hot", [])), set(st.get("fu", []))
    seed = "hot" not in st   # first run: mark existing messages seen, no alert flood (call list covers them)
    convs = get(f"{PAGE}/conversations", platform="messenger",
                fields="participants,messages.limit(20){id,message,from,created_time}", limit=100, access_token=pt).get("data", [])
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = lambda m: datetime.datetime.strptime(m["created_time"], "%Y-%m-%dT%H:%M:%S%z")
    n_hot = n_fu = 0; calls = []
    for c in convs:
        msgs = c.get("messages", {}).get("data") or []          # newest first
        cmsgs = [m for m in msgs if m["from"]["id"] != PAGE]
        if not cmsgs:
            continue
        name, psid = cmsgs[0]["from"].get("name", "?"), cmsgs[0]["from"]["id"]
        recent = [m for m in cmsgs if (now - ts(m)).total_seconds() < 24 * 3600]
        alltext = " | ".join((m.get("message") or "").replace("\n", " ") for m in recent)
        phones = sorted({re.sub(r"\D", "", p)[-10:] for p in PHONE.findall(alltext)})
        # 1. hot lead alert (once per customer message)
        for m in recent:
            t = m.get("message") or ""
            if m["id"] in hot:
                continue
            hot.add(m["id"])
            if seed: continue
            if PHONE.search(t) or QTY.search(t) or BUY.search(t):
                tg(f"🔥 HOT LEAD (Messenger)\n{name}\n\"{t[:300]}\"\n" + (f"📞 {', '.join(phones)}\n" if phones else "📞 number nahi diya: Messenger pe reply karo\n")
                   + "Abhi call / reply karo", dry); n_hot += 1
        # 2. one follow-up: our offer is newer than their last message, no reply since, 18-22 h old
        last = cmsgs[0]; age = (now - ts(last)).total_seconds() / 3600
        offer_after = any(m["from"]["id"] == PAGE and OFFER_MARK in (m.get("message") or "") and ts(m) >= ts(last) for m in msgs)
        # DMs are answered by Meta business AI since 12 Nov: no DM follow-ups (avoid duplicate messages)
        if os.environ.get("DM_FOLLOWUP") == "1" and offer_after and 18 <= age <= 22 and psid not in fu:
            print("follow-up to", name, f"({age:.1f} h)")
            if not dry:
                try:
                    post(f"{PAGE}/messages", pt, {"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": FOLLOW}})
                    n_fu += 1
                except urllib.error.HTTPError as e:
                    print("  failed:", e.read().decode()[:150])
            fu.add(psid)
        # 3. call list material: anyone who wrote in the last 24 h
        if recent:
            calls.append((bool(LOCAL.search(alltext)), name, phones, alltext[:90]))
    # 3. daily call list, first run at/after 09:00 IST
    today = datetime.datetime.now(IST)
    if today.hour >= 9 and st.get("list_day") != today.strftime("%Y-%m-%d"):
        loc = [x for x in calls if x[0]]; rest = [x for x in calls if not x[0]]
        rest.sort(key=lambda x: not x[2])   # people with a number first
        line = lambda i, x: f"{i}. {x[1]} – " + (f"📞 {', '.join(x[2])}" if x[2] else "Messenger") + f" – \"{x[3]}\""
        out = ["📋 Aaj ki call list (Messenger, pichhle 24 ghante)"]
        if loc: out += ["LOCAL (Raipur/Durg/Bhilai):"] + [line(i + 1, x) for i, x in enumerate(loc)]
        if rest: out += ["BAAKI:"] + [line(len(loc) + i + 1, x) for i, x in enumerate(rest[:40])]
        out.append(f"Total: {len(calls)} log" + (f" (list mein pehle 40 baaki dikhaye)" if len(rest) > 40 else ""))
        tg("\n".join(out), dry); st["list_day"] = today.strftime("%Y-%m-%d")
    st["hot"], st["fu"] = list(hot)[-5000:], list(fu)[-3000:]
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"))
    print(f"hot alerts {n_hot}, follow-ups {n_fu}, call-list people {len(calls)}")

if __name__ == "__main__":
    main()
