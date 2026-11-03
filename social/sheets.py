"""Google Sheets helper (Orders sheet). Auth: yt-client.json (desktop OAuth app), token in sheets-token.json (gitignored).
Usage: python social/sheets.py auth | orders-format <tsv>"""
import os, sys, json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, "yt-client.json")
TOKEN = os.path.join(ROOT, "sheets-token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "1O2AqihNecxMMJ6hfqXhrAVP2JcOWN5dI8GlAAZliwSY"
TAB = "Orders"


def creds():
    c = None
    if os.environ.get("SHEETS_TOKEN"):
        c = Credentials.from_authorized_user_info(json.loads(os.environ["SHEETS_TOKEN"]), SCOPES)
    elif os.path.exists(TOKEN):
        c = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if c and c.expired and c.refresh_token:
        c.refresh(Request())
    if not c or not c.valid:
        c = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES).run_local_server(port=0)
        open(TOKEN, "w").write(c.to_json())
    return c


def svc():
    return build("sheets", "v4", credentials=creds()).spreadsheets()


def rgb(h):
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def orders_format(tsv):
    s = svc()
    rows = [l.split("\t") for l in open(tsv, encoding="utf-8").read().strip("\n").split("\n")]
    meta = s.get(spreadsheetId=SHEET_ID).execute()
    sh = next(x for x in meta["sheets"] if x["properties"]["title"] == TAB)
    gid = sh["properties"]["sheetId"]
    reqs = [{"deleteBanding": {"bandedRangeId": b["bandedRangeId"]}} for b in sh.get("bandedRanges", [])]
    reqs += [{"deleteConditionalFormatRule": {"sheetId": gid, "index": 0}} for _ in sh.get("conditionalFormats", [])]
    reqs.append({"updateCells": {"range": {"sheetId": gid}, "fields": "*"}})  # wipe values + formats
    if reqs:
        s.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()
    s.values().update(spreadsheetId=SHEET_ID, range=f"{TAB}!A1", valueInputOption="RAW", body={"values": rows}).execute()
    ncol, last = len(rows[0]), 500
    widths = [40, 60, 250, 120, 110, 120, 90, 45, 70, 90, 420, 160]
    full = {"sheetId": gid, "startRowIndex": 0, "endRowIndex": last, "startColumnIndex": 0, "endColumnIndex": ncol}
    reqs = [
        {"repeatCell": {"range": full, "cell": {"userEnteredFormat": {"wrapStrategy": "CLIP", "verticalAlignment": "MIDDLE",
            "textFormat": {"fontFamily": "Arial", "fontSize": 10}}}, "fields": "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)"}},
        {"repeatCell": {"range": {**full, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": rgb("1F3A5F"),
            "horizontalAlignment": "CENTER", "textFormat": {"bold": True, "foregroundColor": rgb("FFFFFF"), "fontSize": 10}}},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)"}},
        {"addBanding": {"bandedRange": {"range": full, "rowProperties": {"headerColor": rgb("1F3A5F"),
            "firstBandColor": rgb("FFFFFF"), "secondBandColor": rgb("F3F6FA")}}}},
        {"updateSheetProperties": {"properties": {"sheetId": gid, "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 3}},
            "fields": "gridProperties(frozenRowCount,frozenColumnCount)"}},
        {"updateDimensionProperties": {"range": {"sheetId": gid, "dimension": "ROWS", "startIndex": 0, "endIndex": last},
            "properties": {"pixelSize": 28}, "fields": "pixelSize"}},
    ]
    for i, w in enumerate(widths[:ncol]):
        reqs.append({"updateDimensionProperties": {"range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    for c in (0, 1, 7, 8, 9):  # centre short columns
        reqs.append({"repeatCell": {"range": {"sheetId": gid, "startRowIndex": 1, "endRowIndex": last, "startColumnIndex": c, "endColumnIndex": c + 1},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat.horizontalAlignment"}})
    col = lambda c: {"sheetId": gid, "startRowIndex": 1, "endRowIndex": last, "startColumnIndex": c, "endColumnIndex": c + 1}
    for vals, c in ((["Sent", "Not sent", "Pending", "Delivered"], 9), (["Sample", "Full sheet"], 6), (["Free", "199", "Paid", "Pending"], 8)):
        reqs.append({"setDataValidation": {"range": col(c), "rule": {"condition": {"type": "ONE_OF_LIST",
            "values": [{"userEnteredValue": v} for v in vals]}, "showCustomUi": True, "strict": False}}})
    for txt, bg, fg in (("Sent", "D9F2E3", "13653A"), ("Delivered", "D9F2E3", "13653A"), ("Not sent", "FBE0E0", "A12A2A"), ("Pending", "FFF1CC", "8A5A00")):
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [col(9)], "booleanRule": {
            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": txt}]},
            "format": {"backgroundColor": rgb(bg), "textFormat": {"bold": True, "foregroundColor": rgb(fg)}}}}}})
    reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [col(11)], "booleanRule": {
        "condition": {"type": "NOT_BLANK"}, "format": {"textFormat": {"foregroundColor": rgb("B45309"), "bold": True}}}}}})
    s.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()
    print("ok", len(rows) - 1, "rows")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "auth":
        creds(); print("auth ok")
    elif a[0] == "orders-format":
        orders_format(a[1])
