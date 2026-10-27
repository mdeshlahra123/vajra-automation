"""Upload one VAJRA reel to our own YouTube channel (Vajra Formwork) as a Short.
Used by post.yml after the Instagram post. Only ever uploads to the channel that authorised it.

  python social/yt_upload.py <queue-id>          upload that queue item's video
  python social/yt_upload.py <queue-id> --private  upload as private (test)

Env: YT_TOKEN = contents of yt-token.json (client_id, client_secret, refresh_token). Falls back to ./yt-token.json.
Scope: youtube.upload only for writes. No viewer data is read or stored.
"""
import json, os, sys, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOC = os.path.join(ROOT, "social")
SITE = "https://vajraformwork.vercel.app/social/"


def token():
    raw = os.environ.get("YT_TOKEN") or open(os.path.join(ROOT, "yt-token.json"), encoding="utf-8").read()
    t = json.loads(raw)
    body = urllib.parse.urlencode({"client_id": t["client_id"], "client_secret": t["client_secret"],
                                   "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=60))["access_token"]


def meta(item):
    cap = open(os.path.join(SOC, item["caption"]), encoding="utf-8").read().strip()
    first = cap.splitlines()[0].strip()
    title = (first[:90] + " #Shorts").strip()
    tags = ["PP shuttering sheet", "plastic shuttering", "formwork", "shuttering", "VAJRA Formwork", "Raipur", "Chhattisgarh"]
    desc = cap + "\n\nVAJRA Formwork: PP shuttering sheet, Raipur / Durg / Bhilai, pan-India dispatch.\nWebsite: https://vajraformwork.vercel.app"
    return title, desc[:4900], tags


def upload(item, private=False):
    src = item["video"]
    data = urllib.request.urlopen(src if src.startswith("http") else SITE + src, timeout=300).read()
    title, desc, tags = meta(item)
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "22", "defaultLanguage": "hi"},
            "status": {"privacyStatus": "private" if private else "public", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": bool(item.get("ai"))}}
    at = token()
    # resumable upload: 1) create session, 2) send bytes
    req = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))})
    loc = urllib.request.urlopen(req, timeout=60).headers["Location"]
    put = urllib.request.Request(loc, data=data, method="PUT", headers={"Content-Type": "video/mp4"})
    v = json.load(urllib.request.urlopen(put, timeout=600))
    print("YT OK", v["id"], v["status"]["privacyStatus"], "https://youtube.com/shorts/" + v["id"])
    return v["id"]


if __name__ == "__main__":
    q = json.load(open(os.path.join(SOC, "queue.json"), encoding="utf-8"))
    it = next(x for x in q["posts"] if x["id"] == sys.argv[1])
    upload(it, private="--private" in sys.argv)
