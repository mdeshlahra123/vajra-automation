"""One-off: send Shobhit's daily call routine to the Telegram group and pin it. Run via a GitHub workflow (has secrets)."""
import json, os, urllib.request
API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/"
CHAT = os.environ["TELEGRAM_CHAT_ID"]
TEXT = """📞 ROZ KA CALL ROUTINE (Shobhit / Keshav)

Humare reels pe roz 800+ log comment karte hain aur WhatsApp pe message aate hain. Jo jaldi call karega, usi ki sale hogi. Target: har naya lead 2-3 ghante ke andar call ho.

🕘 Subah 9:30 baje:
1. Telegram pe "Aaj ki call list" aati hai — wahi kholo.
2. LOCAL (Raipur / Durg / Bhilai) wale PEHLE call karo. Ye reorder karne wale customers hain.
3. Phir BAAKI city wale.

📞 Call pe kya bolna hai:
- "Namaste, VAJRA Formwork se. Aapne hamari PP shuttering sheet ke baare mein poocha tha."
- Unka sheher aur site poochho (kaunsa kaam chal raha hai).
- Rate: 8x4 ft, 12 mm — ₹3,500 + GST. Sample 1x1 ft — ₹199 (GST + courier included, agle order mein adjust).
- Delivery: poore India, 3-7 din, payment ke baad tracking.
- Claim sirf itna: "Sahi handling ke saath ply se 2-3 guna zyada chalti hai." (koi number mat bolo)

🏷️ Call ke baad label lagao (WhatsApp Business app mein):
- Naya / Rate bheja / Sample paid / Order

🔥 HOT LEAD ping aaye to turant call karo — usne number ya "order/chahiye/50 piece" likha hai, matlab serious hai.

🚫 Jo nahi karna:
- Free sample ab nahi — sirf ₹199 paid.
- Use count ya "X baar chalti hai" kabhi mat bolo.

Har lead pe ek call = ek chance. List khaali mat chhodo."""


def call(method, **p):
    req = urllib.request.Request(API + method, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


r = call("sendMessage", chat_id=CHAT, text=TEXT, disable_web_page_preview=True)
mid = r["result"]["message_id"]
print("sent", mid)
print("pin:", call("pinChatMessage", chat_id=CHAT, message_id=mid, disable_notification=False).get("ok"))
