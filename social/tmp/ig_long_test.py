import json, os, time, urllib.parse, urllib.request
T = os.environ["META_TOKEN"]; IG = "17841424780649708"; V = "https://graph.facebook.com/v24.0/"
URL = "https://github.com/mdeshlahra123/vajra-automation/releases/download/tmp-iglong/iglong.mp4"
def call(path, data=None):
    req = urllib.request.Request(V + path, data=urllib.parse.urlencode(data).encode() if data else None)
    try: return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:300]}
for attempt in range(4):
    c = call(f"{IG}/media", {"media_type": "REELS", "video_url": URL, "caption": "test (not published)", "share_to_feed": "false", "access_token": T})
    if "id" not in c: print("RELEASE-URL container fail", c, flush=True); time.sleep(30); continue
    for _ in range(30):
        s = call(f"{c['id']}?fields=status_code,status&access_token={T}")
        if s.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
        time.sleep(15)
    print("RELEASE-URL try", attempt + 1, s.get("status_code"), s.get("status"), flush=True)
    if s.get("status_code") == "FINISHED": break
    time.sleep(45)
print("NOT PUBLISHED (test only)")