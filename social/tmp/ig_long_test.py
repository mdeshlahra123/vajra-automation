import json, os, time, urllib.parse, urllib.request
T = os.environ["META_TOKEN"]; IG = "17841424780649708"; V = "https://graph.facebook.com/v24.0/"
RAW = "https://raw.githubusercontent.com/mdeshlahra123/vajra-automation/main/"
def call(path, data=None):
    req = urllib.request.Request(V + path, data=urllib.parse.urlencode(data).encode() if data else None)
    try: return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:300]}
def test(label, url):
    c = call(f"{IG}/media", {"media_type": "REELS", "video_url": url, "caption": "test (not published)", "share_to_feed": "false", "access_token": T})
    if "id" not in c: print(label, "CONTAINER FAIL", c); return
    for _ in range(40):
        s = call(f"{c['id']}?fields=status_code,status&access_token={T}")
        if s.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
        time.sleep(15)
    print(label, s.get("status_code"), s.get("status"))
test("CONTROL short reel via raw.githubusercontent", RAW + "social/media/reel-real-1112-1101.mp4")
test("LONG 6 min via raw.githubusercontent (try 1)", RAW + "social/tmp/iglong.mp4")
time.sleep(60)
test("LONG 6 min via raw.githubusercontent (try 2)", RAW + "social/tmp/iglong.mp4")
print("NOT PUBLISHED (test only)")