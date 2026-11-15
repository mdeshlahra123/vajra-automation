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
    """Media models (voice/video/music/image): Gemini billed key only.
    Text/vision models, free stack first (A4):
      server (OmniRoute key present): OmniRoute -> Gemini -> NVIDIA -> Groq
      GitHub / laptop:                Gemini (free key, then billed) -> NVIDIA -> Groq (text only)
    Fallback answers come back in the same Interactions shape, so callers don't change."""
    body = {"model": model, "input": inp}
    if response_format: body["response_format"] = response_format
    if generation_config: body["generation_config"] = generation_config
    if any(m in model for m in MEDIA):
        return _req("interactions", body)
    want_json = bool(response_format and "json" in str(response_format.get("mime_type", "")))
    content, has_img = _oa_content(inp)
    chain = []
    if _omni_key():
        chain.append(("omniroute", lambda: _omni(content, has_img, want_json)))
    chain.append(("gemini", lambda: _req("interactions", body)))
    chain.append(("nvidia", lambda: _oa_call("https://integrate.api.nvidia.com/v1/chat/completions", os.environ.get("NVIDIA_API_KEY"),
                                             "nvidia/nemotron-3.5-super-vl-120b-a12b", content, want_json)))
    if not has_img:
        chain.append(("groq", lambda: _oa_call("https://api.groq.com/openai/v1/chat/completions", os.environ.get("GROQ_API_KEY"),
                                               "llama-3.3-70b-versatile", content, want_json)))
    errs = []
    for name, fn in chain:
        try:
            r = fn()
            if name != "gemini":
                r = _as_interaction(r, want_json)
            if name != chain[0][0]:
                print(f"[gem] answered by {name} (earlier failed: {'; '.join(errs)[:200]})", flush=True)
            return r
        except Exception as e:
            errs.append(f"{name}: {str(e)[:90]}")
    raise RuntimeError("all text/vision providers failed: " + " | ".join(errs))


def _omni_key():
    k = os.environ.get("OMNIROUTE_KEY")
    if k:
        return k
    p = os.path.expanduser("~/.omniroute-vajra.key")
    return open(p).read().strip() if os.path.exists(p) else ""


def _oa_content(inp):
    """Interactions input (str or list of text/image parts) -> OpenAI chat content."""
    if isinstance(inp, str):
        return inp, False
    out, img = [], False
    for p in inp:
        if p.get("type") == "image" and p.get("data"):
            out.append({"type": "image_url", "image_url": {"url": f"data:{p.get('mime_type', 'image/jpeg')};base64,{p['data']}"}}); img = True
        elif p.get("type") == "text":
            out.append({"type": "text", "text": p.get("text", "")})
        elif p.get("type") == "user_input":   # nested form
            c, i = _oa_content(p.get("content", [])); img = img or i
            out += c if isinstance(c, list) else [{"type": "text", "text": c}]
    return out, img


def _oa_call(url, key, model, content, want_json, timeout=180):
    if not key:
        raise RuntimeError("no key")
    if want_json:
        tail = "\n\nReturn ONLY valid JSON, no other text."
        content = content + tail if isinstance(content, str) else content + [{"type": "text", "text": tail}]
    body = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 4000, "temperature": 0.4}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}", "User-Agent": "vajra-bot/1.0"})
    out = (json.load(urllib.request.urlopen(req, timeout=timeout))["choices"][0]["message"].get("content") or "").strip()
    if not out:
        raise RuntimeError("empty answer")
    return out


def _omni(content, has_img, want_json):
    """OmniRoute on the server: vision -> Gemini flash-lite (via OmniRoute), NVIDIA VL, then the claude-free combo."""
    url = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128") + "/v1/chat/completions"
    models = ["gemini/gemini-3.1-flash-lite", "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b", "claude-free"] if has_img else ["claude-free"]
    last = None
    for m in models:
        try:
            return _oa_call(url, _omni_key(), m, content, want_json)
        except Exception as e:
            last = e
    raise last


def _as_interaction(text, want_json):
    if want_json:
        m = re.search(r"\{.*\}|\[.*\]", text, re.S)
        text = m.group(0) if m else text
        json.loads(text)   # bad JSON -> next provider
    return {"steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}]}


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
