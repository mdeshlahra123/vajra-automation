"""Small Gemini API helper (Interactions API, REST, no SDK). Needs env GEMINI_API_KEY."""
import base64, json, os, time, urllib.request, urllib.error

URL = "https://generativelanguage.googleapis.com/v1beta/"


def _req(path, body=None, method=None, timeout=900):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:1500]
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(20 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")


def img_part(path):
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return {"type": "image", "mime_type": mime, "data": base64.b64encode(open(path, "rb").read()).decode()}


def interact(model, inp, response_format=None, generation_config=None):
    body = {"model": model, "input": inp}
    if response_format: body["response_format"] = response_format
    if generation_config: body["generation_config"] = generation_config
    return _req("interactions", body)


def outputs(r):
    """Yield (kind, mime, bytes or text) from model output steps."""
    for s in r.get("steps", []):
        if s.get("type") != "model_output":
            continue
        for c in s.get("content", []):
            t, mime = c.get("type", ""), c.get("mime_type", "")
            if c.get("data"):
                yield t or mime.split("/")[0], mime, base64.b64decode(c["data"])
            elif c.get("text") is not None:
                yield "text", "text/plain", c["text"]


def text(model, prompt, json_mode=False):
    rf = {"type": "text", "mime_type": "application/json"} if json_mode else None
    r = interact(model, prompt, response_format=rf)
    out = "".join(v for k, _, v in outputs(r) if k == "text")
    return json.loads(out) if json_mode else out


def save_first(r, kind, path):
    for k, mime, data in outputs(r):
        if k == kind or mime.startswith(kind):
            open(path, "wb").write(data); return mime
    raise RuntimeError(f"no {kind} in response: " + json.dumps(r)[:1500])


def list_models():
    return [m["name"] for m in _req("models?pageSize=200").get("models", [])]
