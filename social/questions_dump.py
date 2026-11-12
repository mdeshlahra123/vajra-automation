"""One-off: what customers ask (Messenger + FB comments). Prints message TEXT only, phone numbers masked, no names."""
import collections, re, sys
sys.path.insert(0, "social/agent"); import tools
P = tools.PAGE
pt = tools.g(P, fields="access_token")["access_token"]
mask = lambda t: re.sub(r"\d{6,}", "<num>", re.sub(r"\s+", " ", t or "")).strip()[:160]
dm, cm = [], []
convs = tools.g(f"{P}/conversations", platform="messenger", fields="messages.limit(20){message,from}", limit=100, access_token=pt).get("data", [])
for c in convs:
    for m in c.get("messages", {}).get("data", []):
        if m.get("from", {}).get("id") != P and m.get("message"):
            dm.append(mask(m["message"]))
for v in tools.g(f"{P}/videos", fields="id", limit=25, access_token=pt).get("data", []):
    for x in tools.g(f"{v['id']}/comments", fields="message,from", limit=100, access_token=pt).get("data", []):
        if x.get("from", {}).get("id") != P and x.get("message"):
            cm.append(mask(x["message"]))
print("DM_COUNT", len(dm), "COMMENT_COUNT", len(cm))
for name, lst in (("DM", dm), ("COMMENT", cm)):
    cnt = collections.Counter(s.lower() for s in lst)
    print(f"== {name} most common ==")
    for s, n in cnt.most_common(40): print(f"{n:4d} | {s}")
    print(f"== {name} longer questions ==")
    for s in [s for s in dict.fromkeys(lst) if len(s) > 25][:80]: print("   | " + s)
