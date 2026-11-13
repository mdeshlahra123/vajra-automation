"""13 Nov (owner): '💬 Ask' feedback button on EVERY order row that has a phone (it used to hide on Pending / Not sent),
and fix the month column where "Nov" was drag-filled into Dec, Jan, Feb... (rows 43-50, one November batch)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheets as s

x = s.svc()
f = x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!O1", valueRenderOption="FORMULA").execute()["values"][0][0]
old = '(D2:D="")+REGEXMATCH(J2:J&"","^(.*Pending|.*Not sent)?$")'
if old in f:
    f = f.replace(old, '(D2:D="")')
    print("Ask condition: phone only")
else:
    print("Ask condition already changed")
x.values().batchUpdate(spreadsheetId=s.SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": [
    {"range": "Orders!O1", "values": [[f]]},
    {"range": "Orders!B43:B50", "values": [["Nov"]] * 8}]}).execute()

# verify
v = x.values().get(spreadsheetId=s.SHEET_ID, range="Orders!A2:O200").execute().get("values", [])
cell = lambda r, i: r[i].strip() if len(r) > i else ""
miss = [i for i, r in enumerate(v, 2) if cell(r, 3) and not cell(r, 14)]
extra = [i for i, r in enumerate(v, 2) if not cell(r, 3) and cell(r, 14)]
print("rows with phone but no Ask:", miss or "none")
print("Ask on rows without phone:", extra or "none")
print("months in use:", sorted({cell(r, 1) for r in v if cell(r, 2)}))
print("B43-B50:", [cell(r, 1) for r in v[41:49]])
