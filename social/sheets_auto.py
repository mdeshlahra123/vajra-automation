"""Orders sheet autopilot (owner, 13 Nov: "auto populate these things in future"). Safe to run every hour.

1. Month (B): a row with a name/phone but no month gets the current IST month ("Nov"). Written once as text, so it
   never changes later (a formula with TODAY() would) and drag-fill mistakes (Nov -> Dec, Jan...) can't happen.
2. Status (J): a real tracking ID in L (not "recd") while the status is Pending / Not sent / empty -> "📦 Sent".
   Any other status (Thinking, Call back, Ordered...) is never touched.
3. 💬 Ask (O): a button on every row with a phone. Sent/Delivered rows (or rows with a tracking ID) get the
   feedback message; rows not sent yet get an address-confirm message instead, so the button is never wrong.
Prints what it changed. Env SHEETS_TOKEN (GitHub) or sheets-token.json (local)."""
import datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheets as s

PH = '"91"&LEFT(REGEXREPLACE(D2:D&"","\\D",""),10)'
NM = 'IFERROR(REGEXEXTRACT(REGEXREPLACE(C2:C,"(?i)^(shri|mohd\\.?|md\\.?|er\\.?) +",""),"^[A-Za-z]+"),"")'
FEED = ('"Namaste "&' + NM + '&" ji 🙏 VAJRA ka "&LOWER(G2:G)&" mil gaya hoga. Kaisa laga? Ek line mein bata dijiye, '
        'site par use kiya ho to photo bhi bhejein. Full sheet order ke liye: 83050 70160. - Team VAJRA"')
ADDR = ('"Namaste "&' + NM + '&" ji 🙏 VAJRA se. Aapka "&LOWER(G2:G)&" bhejne ke liye apna poora address aur pincode '
        'confirm kar dijiye, hum jaldi dispatch karenge. Kuch poochna ho to: 83050 70160. - Team VAJRA"')
ASK = ('={"Ask feedback";ARRAYFORMULA(IF(D2:D="","",HYPERLINK("https://wa.me/"&' + PH + '&"?text="&ENCODEURL('
       'IF(REGEXMATCH(J2:J&"","Pending|Not sent|^$")*(L2:L=""),' + ADDR + ',' + FEED + ')),"💬 Ask")))}')
TRACK = re.compile(r"^(?=.*\d)[A-Za-z0-9-]{8,}$")   # e.g. 7D146327868, D1021276351 (not "recd")


def main():
    x = s.svc()
    ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    month = ist.strftime("%b")
    v = x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!A2:L500").execute().get("values", [])
    cell = lambda r, i: r[i].strip() if len(r) > i else ""
    data, log = [], []
    for n, r in enumerate(v, 2):
        if not (cell(r, 2) or cell(r, 3)):
            continue
        if not cell(r, 1):
            data.append({"range": f"Orders!B{n}", "values": [[month]]}); log.append(f"row {n}: month {month}")
        st, tr = cell(r, 9), cell(r, 11)
        if TRACK.match(tr) and (st == "" or "Pending" in st or "Not sent" in st):
            data.append({"range": f"Orders!J{n}", "values": [["📦 Sent"]]}); log.append(f"row {n}: {st or 'empty'} -> 📦 Sent (tracking {tr})")
    cur = x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!O1", valueRenderOption="FORMULA").execute()["values"][0][0]
    if cur != ASK:
        data.append({"range": "Orders!O1", "values": [[ASK]]}); log.append("Ask button: message by status")
    if data:
        x.values().batchUpdate(spreadsheetId=s.SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": data}).execute()
    print("\n".join(log) or "nothing to change")


if __name__ == "__main__":
    main()
