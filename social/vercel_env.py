"""Set the /admin page's secrets in the Vercel project (never in the public repo). Uses the local Vercel CLI login
token (AppData) and the local Google sheet token. Prints only names and results, never values.
  python social/vercel_env.py            set SHEETS_TOKEN, ADMIN_PIN, ADMIN_SECRET (production)
  python social/vercel_env.py --pin 5678 change only the PIN"""
import json, os, secrets, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH = os.path.join(os.environ["APPDATA"], "com.vercel.cli", "Data", "auth.json")
TOK = json.load(open(AUTH, encoding="utf-8"))["token"]
API = "https://api.vercel.com"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def project():
    code, j = call("GET", "/v9/projects?limit=50")
    if code != 200:
        sys.exit(f"Vercel login not valid ({code}): {j.get('error', {}).get('message', '')}")
    for p in j.get("projects", []):
        if p["name"] == "vajraformwork" or any("vajraformwork" in str(a) for a in (p.get("alias") or [])):
            return p
    sys.exit("project not found: " + ", ".join(p["name"] for p in j.get("projects", [])))


def main():
    p = project(); pid = p["id"]
    team = f"?teamId={p['accountId']}" if p.get("accountId", "").startswith("team_") else ""
    print("project:", p["name"])
    want = {}
    if "--pin" in sys.argv:
        want["ADMIN_PIN"] = sys.argv[sys.argv.index("--pin") + 1]
    else:
        t = json.load(open(os.path.join(ROOT, "sheets-token.json"), encoding="utf-8"))
        want = {"SHEETS_TOKEN": json.dumps({k: t[k] for k in ("client_id", "client_secret", "refresh_token")}),
                "ADMIN_PIN": "1234", "ADMIN_SECRET": secrets.token_hex(32)}
    code, j = call("GET", f"/v9/projects/{pid}/env{team}")
    have = {e["key"]: e["id"] for e in j.get("envs", [])}
    for k, v in want.items():
        body = {"key": k, "value": v, "type": "encrypted", "target": ["production", "preview"]}
        if k in have:
            code, r = call("PATCH", f"/v9/projects/{pid}/env/{have[k]}{team}", {"value": v, "type": "encrypted", "target": ["production", "preview"]})
        else:
            code, r = call("POST", f"/v10/projects/{pid}/env{team}", body)
        print(k, "->", code, "ok" if code in (200, 201) else r.get("error", {}).get("message", r))


if __name__ == "__main__":
    main()
