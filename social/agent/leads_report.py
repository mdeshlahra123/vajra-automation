"""Lead quality summary from the Meta lead form (who they are, area, city, which ad). Env: META_ADS_TOKEN (or FBT)."""
import collections as C, json, os, urllib.request

if os.path.exists("/tmp/vajra-secrets.json"):
    os.environ.setdefault("META_ADS_TOKEN", json.load(open("/tmp/vajra-secrets.json")).get("META_ADS_TOKEN", ""))
V, T = "https://graph.facebook.com/v24.0/", os.environ.get("META_ADS_TOKEN") or os.environ["FBT"]
g = lambda p: json.load(urllib.request.urlopen(V + p, timeout=40))
pt = g("1296793536861294?fields=access_token&access_token=" + T)["access_token"]
f = g("1296793536861294/leadgen_forms?fields=id,questions&access_token=" + pt)["data"][0]
opts = {q["key"]: {o["key"]: o["value"] for o in q.get("options", [])} for q in f["questions"] if q["type"] == "CUSTOM"}
L = g(f["id"] + "/leads?fields=ad_name,created_time,field_data&limit=200&access_token=" + pt)["data"]
R = [dict([("ad", x.get("ad_name", ""))] + [(d["name"], "/".join(d["values"])) for d in x["field_data"]]) for x in L]
lab = lambda k, v: opts.get(k, {}).get(v, v)
out = {"total": len(R)}
for k in ("buyer_type", "area", "when"):
    out[k] = C.Counter(lab(k, r.get(k, "")) for r in R).most_common(8)
out["city"] = C.Counter(r.get("city", "").strip().lower() for r in R).most_common(12)
out["by_ad"] = {a: {"leads": sum(1 for r in R if r["ad"] == a),
                    "big_area": sum(1 for r in R if r["ad"] == a and r.get("area") in ("a3", "a4"))} for a in {r["ad"] for r in R}}
print(json.dumps(out, ensure_ascii=False, indent=1))
