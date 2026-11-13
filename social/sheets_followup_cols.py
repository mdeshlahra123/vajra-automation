"""13 Nov: add follow-up columns to Orders for the /admin page: R Next follow-up, S Last contact, T Attempts.
Only writes headers if R1:T1 are empty; prints what it did."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheets as s

x = s.svc()
head = x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!A1:T1").execute()["values"][0]
print("header now:", head)
if len(head) > 17 and any(h.strip() for h in head[17:]):
    sys.exit("R1:T1 not empty, nothing changed")
x.values().update(spreadsheetId=s.SHEET_ID, range="Orders!R1:T1", valueInputOption="RAW",
                  body={"values": [["Next follow-up", "Last contact", "Attempts"]]}).execute()
m = x.get(spreadsheetId=s.SHEET_ID).execute()
gid = next(t["properties"]["sheetId"] for t in m["sheets"] if t["properties"]["title"] == "Orders")
reqs = [{"updateDimensionProperties": {"range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                       "properties": {"pixelSize": w}, "fields": "pixelSize"}} for i, w in ((17, 110), (18, 130), (19, 70))]
reqs.append({"repeatCell": {"range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 17, "endColumnIndex": 20},
                            "cell": {"userEnteredFormat": {"backgroundColor": s.rgb("1F3A5F"), "horizontalAlignment": "CENTER",
                                                           "textFormat": {"bold": True, "foregroundColor": s.rgb("FFFFFF")}}},
                            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)"}})
x.batchUpdate(spreadsheetId=s.SHEET_ID, body={"requests": reqs}).execute()
print("header after:", x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!A1:T1").execute()["values"][0][15:])
