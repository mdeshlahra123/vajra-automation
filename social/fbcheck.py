import sys, json
sys.path.insert(0, "social/agent"); import tools
P = tools.PAGE
pt = tools.g(P, fields="access_token")["access_token"]
print(json.dumps(tools.g(P, fields="name,followers_count,fan_count", access_token=pt)))
for m in ("page_views_total", "page_impressions_unique", "page_video_views", "page_follows"):
    try:
        d = tools.g(f"{P}/insights", metric=m, period="days_28", access_token=pt)["data"]
        print(m, d[0]["values"][-1]["value"] if d else None)
    except Exception as e: print(m, "ERR", str(e)[:120])
try:
    print("monetization", json.dumps(tools.g(P, fields="is_eligible_for_branded_content,has_transitioned_to_new_page_experience", access_token=pt)))
except Exception as e: print("mon ERR", str(e)[:150])
