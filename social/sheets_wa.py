"""One-time: add WhatsApp tracking + feedback columns to the Orders sheet (after Tracking ID, col K)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import sheets as s

x = s.svc()
m = x.get(spreadsheetId=s.SHEET_ID).execute()
gid = next(t["properties"]["sheetId"] for t in m["sheets"] if t["properties"]["title"] == "Orders")
N = 500
col = lambda c: {"sheetId": gid, "startRowIndex": 1, "endRowIndex": N, "startColumnIndex": c, "endColumnIndex": c + 1}

# L Send tracking | M Tracking sent | N Ask feedback | O Feedback   (Address -> P, Note -> Q)
reqs = [{"insertDimension": {"range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": 11, "endIndex": 15}, "inheritFromBefore": True}}]
for i, w in zip(range(11, 15), (130, 75, 130, 110)):
    reqs.append({"updateDimensionProperties": {"range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                               "properties": {"pixelSize": w}, "fields": "pixelSize"}})
for c in range(11, 15):
    reqs.append({"repeatCell": {"range": col(c), "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                                "fields": "userEnteredFormat.horizontalAlignment"}})
reqs.append({"setDataValidation": {"range": col(12), "rule": {"condition": {"type": "BOOLEAN"}}}})
reqs.append({"setDataValidation": {"range": col(14), "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
    {"userEnteredValue": v} for v in ("Asked", "👍 Good", "😐 OK", "👎 Bad", "No reply", "Ordered")]}, "showCustomUi": True, "strict": False}}})
for txt, bg, fg in (("👍 Good", "D9F2E3", "13653A"), ("Ordered", "C7EBD3", "0B4D2A"), ("👎 Bad", "FBE0E0", "A12A2A"), ("Asked", "FFF1CC", "8A5A00")):
    reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [col(14)], "booleanRule": {
        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": txt}]},
        "format": {"backgroundColor": s.rgb(bg), "textFormat": {"bold": True, "foregroundColor": s.rgb(fg)}}}}}})
x.batchUpdate(spreadsheetId=s.SHEET_ID, body={"requests": reqs}).execute()

PH = '"91"&LEFT(REGEXREPLACE(D2:D,"\\D",""),10)'
NM = 'IFERROR(REGEXEXTRACT(C2:C,"^[A-Za-z]+"),"")'
TRACK = ('"Namaste "&' + NM + '&" ji 🙏 VAJRA se aapka "&LOWER(G2:G)&" parcel bhej diya gaya hai. Tracking ID: "&K2:K&'
         '". 2-5 din mein pahunch jayega. Kuch bhi poochna ho to call/WhatsApp karein: 83050 70160. - Team VAJRA"')
FEED = ('"Namaste "&' + NM + '&" ji 🙏 VAJRA ka "&LOWER(G2:G)&" mil gaya hoga. Kaisa laga? Ek line mein bata dijiye, '
        'site par use kiya ho to photo bhi bhejein. Full sheet order ke liye: 83050 70160. - Team VAJRA"')
f_track = ('={"Send tracking";ARRAYFORMULA(IF((K2:K="")+(D2:D=""),"",HYPERLINK("https://wa.me/"&' + PH +
           '&"?text="&ENCODEURL(' + TRACK + '),"📦 Send")))}')
f_feed = ('={"Ask feedback";ARRAYFORMULA(IF((D2:D="")+NOT(REGEXMATCH(J2:J&"","^(Sent|Delivered)$")),"",HYPERLINK("https://wa.me/"&' + PH +
          '&"?text="&ENCODEURL(' + FEED + '),"💬 Ask")))}')
x.values().batchUpdate(spreadsheetId=s.SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": [
    {"range": "Orders!L1", "values": [[f_track]]},
    {"range": "Orders!M1", "values": [["Tracking sent"]]},
    {"range": "Orders!N1", "values": [[f_feed]]},
    {"range": "Orders!O1", "values": [["Feedback"]]},
]}).execute()
print(x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!A1:Q3").execute()["values"])
