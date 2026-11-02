"""Daily Meta ads manager for VAJRA (runs on GitHub, no laptop needed).

Hard rules (user's money rule): NEVER change budgets, bids or targeting, NEVER add money.
It only pauses / resumes ads that already exist in the account, and reports to Telegram.

Rules, using the last 7 days:
  - pause an active ad that spent >= MIN_SPEND with 0 leads
  - pause an active ad whose cost per lead is > WORSE x the best active ad (after >= MIN_SPEND)
  - always keep at least MIN_ACTIVE ads running: if fewer, resume the paused ad with the best lifetime cost per lead
    (ads paused by this script in the last COOLDOWN days are skipped)
  - alert when the prepaid balance is low
Env: META_ADS_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. State: social/ads-state.json
"""
import datetime, json, os, urllib.parse, urllib.request

ACCOUNT = "act_1417609487254050"
V = "https://graph.facebook.com/v24.0/"
TOK = os.environ["META_ADS_TOKEN"]
# 2 Nov (owner: full automation): judge after Rs 60 (Rs 100/day split over ~5 ads means few ads ever reach 150),
# pause when cost/chat is > 1.8x the best running ad. Still never touches budgets.
MIN_SPEND, WORSE, MIN_ACTIVE, COOLDOWN, LOW_BAL = 60.0, 1.8, 2, 7, 200.0
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ads-state.json")
DRY = os.environ.get("DRY_RUN") == "true"
# ads whose text breaks the use-count rule (40+ / lakh maths) or use banned footage: never resume
# owner (27 Oct): permanent ads, never paused by this script until the owner says
KEEP = set()  # samples ad paused 27 Oct (₹23/chat vs ₹3-5); owner gave full control
NEVER = {"120251541042410600", "120251501523230600", "120251451378980600", "120251451052520600", "120251501107770600"}


def get(path, **p):
    p["access_token"] = TOK
    return json.load(urllib.request.urlopen(V + path + "?" + urllib.parse.urlencode(p), timeout=60))


def post(path, **p):
    p["access_token"] = TOK
    return json.load(urllib.request.urlopen(urllib.request.Request(V + path, data=urllib.parse.urlencode(p).encode()), timeout=60))


def leads(row):
    return sum(float(a["value"]) for a in row.get("actions", []) if a["action_type"] in ("lead", "onsite_conversion.messaging_conversation_started_7d"))


def insights(preset):
    r = get(f"{ACCOUNT}/insights", level="ad", date_preset=preset, fields="ad_id,ad_name,spend,actions,ctr", limit=200)
    return {x["ad_id"]: {"spend": float(x["spend"]), "leads": leads(x), "ctr": float(x.get("ctr", 0)), "name": x["ad_name"]} for x in r.get("data", [])}


def tg(text):
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                                 data=json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)


def main():
    today = datetime.date.today()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"paused_by_bot": {}}
    ads = {a["id"]: a for a in get(f"{ACCOUNT}/ads", fields="name,status,effective_status", limit=200)["data"]}
    w7, life, y = insights("last_7d"), insights("maximum"), insights("yesterday")
    active = [i for i, a in ads.items() if a["effective_status"] == "ACTIVE"]
    actions = []

    def cpl(d):
        return d["spend"] / d["leads"] if d and d["leads"] else None

    best = min([c for c in (cpl(w7.get(i)) for i in active) if c] or [None]) if active else None
    for i in list(active):
        d = w7.get(i)
        if i in KEEP or not d or d["spend"] < MIN_SPEND or len(active) <= MIN_ACTIVE:
            continue
        c = cpl(d)
        why = "0 leads" if not c else (f"₹{c:.0f}/lead vs best ₹{best:.0f}" if best and c > WORSE * best else None)
        if why:
            actions.append(("pause", i, why)); active.remove(i)
    if len(active) < MIN_ACTIVE:
        cands = [i for i, a in ads.items() if a["status"] == "PAUSED" and i not in active and cpl(life.get(i)) and i not in NEVER
                 and (today - datetime.date.fromisoformat(state["paused_by_bot"].get(i, "2000-01-01"))).days >= COOLDOWN]
        for i in sorted(cands, key=lambda i: cpl(life[i]))[: MIN_ACTIVE - len(active)]:
            actions.append(("resume", i, f"best paused ad, lifetime ₹{cpl(life[i]):.0f}/lead")); active.append(i)

    # planned swap (owners OK'd 25 Oct): WhatsApp test L7 has old "40+ / 1.1 lakh" text -> L8 Throw reel with the 2-3 guna line,
    # once the test has its ~Rs 300 or on 28 Oct, whichever comes first. Same ad set, same budget.
    L7, L8 = "120251541042410600", "120251567184010600"
    if False and not state.get("l8_swap") and L7 in ads and L8 in ads and (life.get(L7, {}).get("spend", 0) >= 300 or today >= datetime.date(2026, 10, 28)):
        d7 = life.get(L7, {})
        actions += [("resume", L8, "naya WhatsApp ad, 2-3 guna text"), ("pause", L7, f"test poora: ₹{d7.get('spend', 0):.0f}, {d7.get('leads', 0):.0f} chats, purana 40+ text")]
        active = [x for x in active if x != L7] + [L8]; state["l8_swap"] = today.isoformat()
    for act, i, why in actions:
        if not DRY:
            post(i, status="PAUSED" if act == "pause" else "ACTIVE")
            if act == "pause":
                state["paused_by_bot"][i] = today.isoformat()
    json.dump(state, open(STATE, "w"), indent=2)

    acc = get(ACCOUNT, fields="funding_source_details,amount_spent")
    bal_txt = acc.get("funding_source_details", {}).get("display_string", "")
    try:
        bal = float(bal_txt.split("₹")[1].split()[0].replace(",", ""))
    except Exception:
        bal = None
    ys = sum(d["spend"] for d in y.values()); yl = sum(d["leads"] for d in y.values())
    ws = sum(d["spend"] for d in w7.values()); wl = sum(d["leads"] for d in w7.values())
    lines = [f"📊 VAJRA ads · {today:%d %b}",
             f"Kal: ₹{ys:.0f} kharch, {yl:.0f} leads" + (f" (₹{ys/yl:.0f}/lead)" if yl else ""),
             f"7 din: ₹{ws:.0f}, {wl:.0f} leads" + (f" (₹{ws/wl:.0f}/lead)" if wl else ""), "", "Chal rahe ads:"]
    for i in active:
        d = w7.get(i, {"spend": 0, "leads": 0, "ctr": 0})
        lines.append(f"• {ads[i]['name'][:40]}: ₹{d['spend']:.0f}, {d['leads']:.0f} leads" + (f", ₹{d['spend']/d['leads']:.0f}/lead" if d["leads"] else ""))
    if actions:
        lines += ["", "Aaj ke badlav:"] + [f"• {'⏸ Paused' if a == 'pause' else '▶️ Resumed'}: {ads[i]['name'][:40]} ({why})" for a, i, why in actions]
    if bal is not None and bal < LOW_BAL:
        lines += ["", f"⚠️ Balance sirf ₹{bal:.0f} bacha hai. Khatam hone par ads ruk jayenge. Top-up aapka faisla hai, main nahi karunga."]
    elif bal is not None:
        lines.append(f"\nBalance: ₹{bal:.0f}")
    text = "\n".join(lines) + ("\n(DRY RUN, kuch badla nahi)" if DRY else "")
    print(text); tg(text)


if __name__ == "__main__":
    main()
