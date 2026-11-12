import json, os, time, urllib.parse, urllib.request
T = os.environ["META_TOKEN"]; IG = "17841424780649708"; V = "https://graph.facebook.com/v24.0/"
url = "https://raw.githubusercontent.com/mdeshlahra123/vajra-automation/main/social/tmp/iglong.mp4"
def call(path, data=None):
    req = urllib.request.Request(V + path, data=urllib.parse.urlencode(data).encode() if data else None)
    try: return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:400]}
c = call(f"{IG}/media", {"media_type": "REELS", "video_url": url, "caption": "test (not published)", "share_to_feed": "false", "access_token": T})
print("CONTAINER", c)
if "id" in c:
    for i in range(30):
        s = call(f"{c['id']}?fields=status_code,status&access_token={T}"); print("STATUS", s)
        if s.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
        time.sleep(20)
print("NOT PUBLISHED (test only)")