"""Small Gemini API helper (Interactions API, REST, no SDK).
Env: GEMINI_API_KEY (billed: video/voice/music), GEMINI_FREE_KEY (free tier: text/vision, tried first), GROQ_API_KEY (text fallback)."""
import base64, json, os, re, time, urllib.request, urllib.error

URL = "https://generativelanguage.googleapis.com/v1beta/"


MEDIA = ("tts", "omni", "lyria", "veo", "image", "imagen")  # media models need the billed key


def _keys(body):
    """Text models: free-tier key first (no billing, no spend cap), then the billed key. Media models: billed key only."""
    model = str((body or {}).get("model", ""))
    keys = [os.environ.get("GEMINI_API_KEY")] if any(m in model for m in MEDIA) else [os.environ.get("GEMINI_FREE_KEY"), os.environ.get("GEMINI_API_KEY")]
    return [k for k in keys if k]


def _req(path, body=None, method=None, timeout=900):
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for key in _keys(body) or [""]:
        req = urllib.request.Request(URL + path, data=data, method=method or ("POST" if data else "GET"),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        for attempt in range(3):
            try:
                return json.load(urllib.request.urlopen(req, timeout=timeout))
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:1500]
                last = RuntimeError(f"HTTP {e.code}: {msg}")
                ml = msg.lower()
                # this key is out (spend cap / daily quota / rate limit) -> try the next key (billed after free)
                if e.code in (403, 429) and any(w in ml for w in ("cap", "quota", "exhausted", "rate limit", "too_many_requests", "limit:")):
                    break
                if e.code in (429, 500, 503) and attempt < 2:
                    time.sleep(20 * (attempt + 1)); continue
                raise last
    raise last


def groq(prompt, json_mode=False, model="llama-3.3-70b-versatile"):
    """Last-resort text fallback (free Groq tier, OpenAI-compatible). Text only, no images."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("no GROQ_API_KEY")
    body = {"model": model, "messages": [{"role": "user", "content": prompt if isinstance(prompt, str) else json.dumps(prompt)}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}", "User-Agent": "vajra-bot/1.0"})
    out = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"]
    return json.loads(out) if json_mode else out


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


def nvidia(prompt, json_mode=False, model="nvidia/nemotron-3.5-super-vl-120b-a12b"):
    """Free NVIDIA NIM (build.nvidia.com, ~10k requests/day). Text only."""
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY")
    p = prompt if isinstance(prompt, str) else json.dumps(prompt)
    if json_mode:
        p += "\n\nReturn ONLY valid JSON, no other text."
    body = {"model": model, "messages": [{"role": "user", "content": p}], "max_tokens": 4000, "temperature": 0.4}
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}", "User-Agent": "vajra-bot/1.0"})
    out = json.load(urllib.request.urlopen(req, timeout=180))["choices"][0]["message"]["content"] or ""
    if not json_mode:
        return out
    m = re.search(r"\{.*\}", out, re.S)
    return json.loads(m.group(0) if m else out)


def text(model, prompt, json_mode=False):
    rf = {"type": "text", "mime_type": "application/json"} if json_mode else None
    try:
        r = interact(model, prompt, response_format=rf)
    except RuntimeError:
        if isinstance(prompt, str) and os.environ.get("GROQ_API_KEY"):
            return groq(prompt, json_mode)  # Gemini keys all out: free Groq for plain text
        raise
    out = "".join(v for k, _, v in outputs(r) if k == "text")
    return json.loads(out) if json_mode else out


def save_first(r, kind, path):
    for k, mime, data in outputs(r):
        if k == kind or mime.startswith(kind):
            open(path, "wb").write(data); return mime
    raise RuntimeError(f"no {kind} in response: " + json.dumps(r)[:1500])


def list_models():
    return [m["name"] for m in _req("models?pageSize=200").get("models", [])]
