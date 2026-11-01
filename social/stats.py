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
# FB: metrics tried one by one (reels and normal videos accept different names)
FB_METRICS = ["blue_reels_play_count", "fb_reels_total_plays", "post_impressions_unique", "post_video_followers",
              "post_video_social_actions", "post_video_avg_time_watched", "total_video_views", "total_video_views_unique",
              "total_video_avg_time_watched", "total_video_impressions_unique"]
try:
    pt = g(PAGE, fields="access_token").get("access_token")
    tok = {"access_token": pt} if pt else {}
    for v in g(f"{PAGE}/videos", fields="id,created_time,description,length,post_id", limit=14, **tok)["data"]:
        r = {"date": v["created_time"][:16], "len": round(v.get("length") or 0, 1), "hook": (v.get("description") or "").split("\n")[0][:50]}
        for mt in FB_METRICS:
            try:
                d = g(f"{v['id']}/video_insights", metric=mt, **tok)["data"]
                if d: r[mt] = d[0]["values"][0]["value"]
            except Exception:
                pass
        if v.get("post_id"):
            try:
                p = g(f"{PAGE}_{v['post_id']}" if "_" not in str(v["post_id"]) else v["post_id"], fields="reactions.summary(true),comments.summary(true),shares", **tok)
                r["reactions"] = p.get("reactions", {}).get("summary", {}).get("total_count")
                r["comments"] = p.get("comments", {}).get("summary", {}).get("total_count")
                r["shares"] = (p.get("shares") or {}).get("count")
            except Exception:
                pass
        out["fb"].append(r)
except Exception as e:
    out["fb_error"] = str(e)[:200]
print(json.dumps(out, ensure_ascii=False, indent=1))
