# VAJRA WhatsApp automation — status & next steps

_Last updated: 1 Nov 2026_

## Goal
Smart auto-replies + one follow-up + hot-lead Telegram alerts + daily call list on VAJRA's WhatsApp
**83050 70160**, free, while keeping the number working in the WhatsApp Business app (coexistence).

## Approach (decided 1 Nov)
- **Planstalk LLP** (already a verified Meta business) is an **Independent Tech Provider**.
- **VAJRA connects as the client** through Meta **Embedded Signup with coexistence** — number stays in the app.
- No GST/Udyam needed (Planstalk is verified). **No paid BSP** (Wati/AiSensy). **No Baileys/whatsapp-web.js** (ban
  risk). **No new number.**
- Money rule: we never add a payment method on Meta, and the bot only replies inside Meta's free window
  (24 h after the customer writes, 72 h for click-to-WhatsApp ad chats). So nothing can be charged.

## Meta app
- **Name:** Planstalk Connect — **App ID:** 1826605545131587 — Live — business: **Planstalk**
- **Use cases:** WhatsApp + Messenger + Instagram
- **Test number:** +1 555 172 6507 — **Phone Number ID:** 1424622750730437 — **WABA:** 1510641854208733
- **Website/privacy for review:** https://www.planstalk.com/connect and privacy-policy section 5 (both live)

## Current state: ⏳ APP REVIEW SUBMITTED (1 Nov)
Requested: `whatsapp_business_messaging`, `whatsapp_business_management`, `public_profile`.
Status "Review in progress" — Meta says up to 20 days, usually faster.
Decision arrives at the **Planstalk email** + the app's **Alert Inbox**.

## When Meta responds
- **Approved:** 
  1. Run **Embedded Signup** (coexistence) to connect **83050 70160**. Number keeps working in the app.
  2. Create a permanent **system-user token** -> add GitHub secret **WA_TOKEN**. Set `WA_PHONE_ID` + `WA_WABA_ID`
     to VAJRA's live ones.
  3. Stand up a free **Cloudflare Worker** webhook that receives each inbound message and calls
     `wa_bot.process_message(...)`. Add a `wa.yml` (or reuse messenger.yml) step.
  4. Test on a personal number first, then go live.
- **Changes requested:** forward Meta's note. Usual asks = clearer demo video or wording tweak (quick).

## Bot already built (parked): `social/wa_bot.py`
- Offer + ₹199 card on first message; claims-safe keyword answers (rate/sample/size/delivery/ply/payment).
- Hot-lead Telegram alert on phone/qty/buying words, LOCAL-tagged for Raipur/Durg/Bhilai.
- One follow-up, inside the free window only.
- All reply texts pass `social/engine/claims.py` (no use-count, no fake proof, 199 sample, 3500+GST).
- **Test-number / dry only** and **not wired into any workflow** until approval.
- Dry test: `python social/wa_bot.py --reply 919876543210 "rate 50 piece durg"`

## Demo videos (for re-submission if asked)
On the laptop in **Videos\Captures**: Video 1 = send message arriving in WhatsApp; Video 2 = create template (PENDING).
