"""Upload VAJRA reels to our own YouTube channel (Vajra Formwork) as Shorts. Audit passed 28 Oct 2026.

  python social/yt_upload.py                  upload today's posted reels that are not on YouTube yet (run after daily-post)
  python social/yt_upload.py <queue-id>       upload that queue item now
  python social/yt_upload.py <queue-id> --private

After upload: sets our cover as thumbnail (if allowed), adds the Short to the "VAJRA PP Shuttering" playlist,
and marks the queue item with "yt": <videoId> so it is never uploaded twice.
Env: YT_TOKEN = contents of yt-token.json. Falls back to ./yt-token.json.
"""
import datetime, json, os, sys, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOC = os.path.join(ROOT, "social")
SITE = "https://vajraformwork.vercel.app/social/"
YT = "https://www.googleapis.com/youtube/v3/"
PLAYLIST = "VAJRA PP Shuttering"


def token():
    raw = os.environ.get("YT_TOKEN") or open(os.path.join(ROOT, "yt-token.json"), encoding="utf-8").read()
    t = json.loads(raw)
    body = urllib.parse.urlencode({"client_id": t["client_id"], "client_secret": t["client_secret"],
                                   "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=60))["access_token"]


def api(at, method, path, body=None, ctype="application/json"):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(YT + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {at}", "Content-Type": ctype})
    r = urllib.request.urlopen(req, timeout=120).read()
    return json.loads(r) if r else {}


def meta(item):
    cap = open(os.path.join(SOC, item["caption"]), encoding="utf-8").read().strip()
    first = cap.splitlines()[0].strip()
    title = (first[:90] + " #Shorts").strip()
    tags = ["PP shuttering sheet", "plastic shuttering", "formwork", "shuttering", "VAJRA Formwork", "Raipur", "Chhattisgarh"]
    desc = cap + "\n\nVAJRA Formwork: PP shuttering sheet, Raipur / Durg / Bhilai, pan-India dispatch.\nWebsite: https://vajraformwork.vercel.app"
    return title, desc[:4900], tags


def playlist_id(at):
    r = api(at, "GET", "playlists?part=snippet&mine=true&maxResults=50")
    for p in r.get("items", []):
        if p["snippet"]["title"] == PLAYLIST:
            return p["id"]
    return api(at, "POST", "playlists?part=snippet,status", {"snippet": {"title": PLAYLIST,
               "description": "VAJRA PP shuttering sheet: site videos, column, slab, beam."}, "status": {"privacyStatus": "public"}})["id"]


def upload(item, private=False):
    src = item["video"]
    data = urllib.request.urlopen(src if src.startswith("http") else SITE + src, timeout=300).read()
    title, desc, tags = meta(item)
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "22", "defaultLanguage": "hi"},
            "status": {"privacyStatus": "private" if private else "public", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": bool(item.get("ai"))}}
    at = token()
    req = urllib.request.Request(YT.replace("/youtube/v3/", "/upload/youtube/v3/") + "videos?uploadType=resumable&part=snippet,status",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))})
    loc = urllib.request.urlopen(req, timeout=60).headers["Location"]
    v = json.load(urllib.request.urlopen(urllib.request.Request(loc, data=data, method="PUT", headers={"Content-Type": "video/mp4"}), timeout=600))
    vid = v["id"]
    print("YT OK", vid, v["status"]["privacyStatus"], "https://youtube.com/shorts/" + vid)
    if item.get("cover"):
        try:
            img = urllib.request.urlopen(item["cover"], timeout=60).read()
            req = urllib.request.Request(YT.replace("/youtube/v3/", "/upload/youtube/v3/") + f"thumbnails/set?videoId={vid}", data=img,
                                         method="POST", headers={"Authorization": f"Bearer {at}", "Content-Type": "image/jpeg"})
            urllib.request.urlopen(req, timeout=60); print("  cover set")
        except Exception as e:
            print("  cover skipped:", str(e)[:120])
    try:
        api(at, "POST", "playlistItems?part=snippet", {"snippet": {"playlistId": playlist_id(at), "resourceId": {"kind": "youtube#video", "videoId": vid}}})
        print("  added to playlist")
    except Exception as e:
        print("  playlist skipped:", str(e)[:120])
    return vid


if __name__ == "__main__":
    p = os.path.join(SOC, "queue.json")
    q = json.load(open(p, encoding="utf-8"))
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    items = [x for x in q["posts"] if x["id"] in args] if args else \
            [x for x in q["posts"] if x.get("video") and x.get("posted") == today and not x.get("yt")]
    for it in items:
        try:
            it["yt"] = upload(it, private="--private" in sys.argv)
        except Exception as e:
            print("YT FAIL", it["id"], str(e)[:300])
    json.dump(q, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a", encoding="utf-8").write("\n")
