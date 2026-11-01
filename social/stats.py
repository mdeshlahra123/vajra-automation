"""Read-only organic stats: last 14 IG posts and last 14 FB page videos (manual: stats.yml)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
import tools  # uses META_ADS_TOKEN

g, PAGE = tools.g, tools.PAGE
out = {"ig": [], "fb": []}
ig = g(PAGE, fields="instagram_business_account")["instagram_business_account"]["id"]
out["followers"] = g(ig, fields="followers_count").get("followers_count")
for m in g(f"{ig}/media", fields="id,timestamp,media_product_type,like_count,comments_count,caption", limit=14)["data"]:
    r = {"date": m["timestamp"][:16], "type": m.get("media_product_type"), "likes": m.get("like_count"),
         "comments": m.get("comments_count"), "hook": (m.get("caption") or "").split("\n")[0][:50]}
    try:
        r.update({x["name"]: x["values"][0]["value"] for x in g(f"{m['id']}/insights", metric="reach,saved,shares,views")["data"]})
    except Exception as e:
        r["err"] = str(e)[:80]
    out["ig"].append(r)
try:
    pt = g(PAGE, fields="access_token").get("access_token")
    tok = {"access_token": pt} if pt else {}
    for v in g(f"{PAGE}/videos", fields="id,created_time,description,length", limit=14, **tok)["data"]:
        r = {"date": v["created_time"][:16], "len": round(v.get("length") or 0, 1), "hook": (v.get("description") or "").split("\n")[0][:50]}
        try:
            for x in g(f"{v['id']}/video_insights", metric="total_video_views,total_video_views_unique,total_video_avg_time_watched", **tok)["data"]:
                r[x["name"].replace("total_video_", "")] = x["values"][0]["value"]
        except Exception as e:
            r["err"] = str(e)[:80]
        out["fb"].append(r)
except Exception as e:
    out["fb_error"] = str(e)[:200]
print(json.dumps(out, ensure_ascii=False, indent=1))
