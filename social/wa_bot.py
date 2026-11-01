"""VAJRA WhatsApp auto-reply + follow-up + hot-lead alerts (built 1 Nov, PARKED until Meta approves Planstalk Connect).

Until the Planstalk Connect app review passes and VAJRA's number 83050 70160 is connected via Embedded Signup
(coexistence), this ONLY runs against the Meta test number, and only in --dry or --test mode. It is NOT wired into
any workflow yet. When approval lands: set PHONE_NUMBER_ID + WABA_ID to the live ones, add WA_TOKEN secret, and add a
step to messenger.yml (or a new wa.yml) that runs `python social/wa_bot.py`.

How WhatsApp Cloud API differs from the Messenger bot:
- We receive messages via a WEBHOOK (Meta POSTs each inbound message to our URL), not by polling conversations.
  So the live deployment needs a tiny always-on receiver (free Cloudflare Worker) that appends each message to a
  store this script reads. For now this file has: (a) the reply/brain logic, (b) a --test mode that sends to the
  test number, (c) a process_message() the webhook will call. No polling, because Cloud API has no "list all chats".
- Free windows: inside 24 h of the customer's last message (72 h if they came from a click-to-WhatsApp ad), all
  replies are free. We never send outside the window (that needs paid templates) -> money rule safe.

Env: WA_TOKEN (permanent system-user token, added at approval), TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
Usage:
  python social/wa_bot.py --test "<your number>"   # send the offer to one number via the TEST sender
  python social/wa_bot.py --reply "<from>" "<text>"  # dry: print what we WOULD reply to a given message
"""
import datetime, json, os, re, sys, urllib.parse, urllib.request

V = "https://graph.facebook.com/v24.0"
# TEST values (Meta-provided). Swap to live VAJRA number at approval.
PHONE_NUMBER_ID = os.environ.get("WA_PHONE_ID", "1424622750730437")
WABA_ID = os.environ.get("WA_WABA_ID", "1510641854208733")
BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "wa-state.json")
SITE = "https://vajraformwork.vercel.app"
OFFER_IMG = f"{SITE}/social/msg-offer.jpg"   # 199/- offer card (design 1)
OFFER_MARK = "VAJRA PP shuttering sheet"
OFFER = ("Namaste ji 🙏\n"
         "VAJRA PP shuttering sheet: ₹3,500 + GST (8x4 ft, 12 mm).\n\n"
         "Sample (1x1 ft) bhi milta hai, 199/-\n\n"
         "Sample ya rate ke liye apna naam aur shehar bheje - call/WhatsApp karein: 83050 70160\n\n"
         f"👉 {SITE}/try")
FOLLOW = ("Namaste ji 🙏 Kal aapne VAJRA PP sheet ke baare mein poocha tha.\n"
          "Aap kis shehar se hain? Rate, delivery aur ₹199 sample ki poori jaankari de dete hain.\n"
          "📞 Call/WhatsApp: 83050 70160")

PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
QTY = re.compile(r"\b\d+\s*(?:pis|pish|pees|piece|pieces|pcs|pc|sheet|sheets|seet|shit|nag|पीस|शीट)\b", re.I)
BUY = re.compile(r"order|chahiye|chaiye|chahie|bhejo|bhej do|bhejiye|address|upi|payment|kab tak|delivery|"
                 r"चाहिए|भेजो|भेज|ऑर्डर|आर्डर|पेमेंट", re.I)
LOCAL = re.compile(r"raipur|durg|bhilai|रायपुर|दुर्ग|भिलाई", re.I)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# Quick keyword answers (claims-safe; no use-count, no fake proof, 199 sample, 3500+GST sheet).
QA = [
    (re.compile(r"\brate|price|kitne|kitna|daam|cost\b", re.I),
     "VAJRA PP shuttering sheet: ₹3,500 + GST (8x4 ft, 12 mm). 1x1 ft sample 199/- (GST + courier included, agle order mein adjust). 📞 83050 70160"),
    (re.compile(r"sample", re.I),
     "1x1 ft sample 199/- (GST + courier included, agle order mein adjust). Apna naam, address aur pincode bheje — UPI ID bhej dete hain. 📞 83050 70160"),
    (re.compile(r"size|8x4|12\s*mm|dimension|mota", re.I),
     "Sheet 8x4 ft, 12 mm. Cutter se size mein aaram se kat jaati hai. 📞 83050 70160"),
    (re.compile(r"deliver|courier|bhej|transport|kaise aayeg|kahan", re.I),
     "Poore India mein courier se bhejte hain, 3–7 din. Payment ke baad tracking WhatsApp pe. 📞 83050 70160"),
    (re.compile(r"ply|plywood|kyun|faayda|benefit|achha", re.I),
     "PP sheet waterproof hai aur sahi handling ke saath ply se 2-3 guna zyada chalti hai. Paani se kharab nahi hoti, finish smooth. 📞 83050 70160"),
    (re.compile(r"\bupi|payment|paisa|pay\b", re.I),
     "Order confirm karne ke liye naam, address, pincode bheje — UPI ID bhej dete hain. Payment ke baad dispatch. 📞 83050 70160"),
]


def send(payload, dry):
    if dry:
        print("WA>>", json.dumps(payload, ensure_ascii=False)[:400]); return {"dry": True}
    body = json.dumps({"messaging_product": "whatsapp", **payload}).encode()
    req = urllib.request.Request(f"{V}/{PHONE_NUMBER_ID}/messages?access_token={os.environ['WA_TOKEN']}",
                                 data=body, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def tg(text, dry):
    if dry or not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("TG>>", text); return
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                                 data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:3900]}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)


def answer_for(text):
    """Pick a claims-safe reply. First message or no keyword -> full offer; else the matching quick answer."""
    for rx, ans in QA:
        if rx.search(text or ""):
            return ans
    return OFFER


def process_message(wa_id, name, text, first_time, dry=True):
    """Called by the webhook for each inbound message. Returns what we did.
    - Sends the offer card + text on the first message, else a quick keyword answer.
    - Fires a Telegram hot-lead alert if the message has a phone/qty/buying words.
    - Never messages outside Meta's free window (the webhook only fires on inbound, which opens the window)."""
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    hot = set(st.get("hot", []))
    done = set(st.get("seen", []))

    sent = []
    if first_time:
        send({"to": wa_id, "type": "image", "image": {"link": OFFER_IMG}}, dry)
        send({"to": wa_id, "type": "text", "text": {"body": OFFER}}, dry)
        sent.append("offer+card")
    else:
        send({"to": wa_id, "type": "text", "text": {"body": answer_for(text)}}, dry)
        sent.append("answer")

    key = f"{wa_id}:{hash(text)}"
    phones = sorted({re.sub(r'\D', '', p)[-10:] for p in PHONE.findall(text or "")}) or [wa_id[-10:]]
    if key not in hot and (PHONE.search(text or "") or QTY.search(text or "") or BUY.search(text or "")):
        tag = "LOCAL " if LOCAL.search(text or "") else ""
        tg(f"🔥 {tag}HOT LEAD (WhatsApp)\n{name}\n\"{(text or '')[:300]}\"\n📞 {', '.join(phones)}\nAbhi call karo", dry)
        hot.add(key); sent.append("alert")

    done.add(wa_id)
    st["hot"], st["seen"] = list(hot)[-5000:], list(done)[-5000:]
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"))
    return sent


def main():
    a = sys.argv
    if "--test" in a:
        # Send the real offer to one number through the TEST sender (number must be a verified test recipient).
        num = a[a.index("--test") + 1]
        print("sending offer to", num)
        send({"to": num, "type": "text", "text": {"body": OFFER}}, dry=False)
        return
    if "--reply" in a:
        # Dry: show what we'd reply to a given message, and whether it would alert.
        i = a.index("--reply"); frm = a[i + 1]; txt = a[i + 2] if len(a) > i + 2 else ""
        print("first-message reply:"); process_message(frm, "Test User", "", True, dry=True)
        print("\nquick answer to", repr(txt), ":"); process_message(frm, "Test User", txt, False, dry=True)
        return
    print(__doc__)


if __name__ == "__main__":
    main()
