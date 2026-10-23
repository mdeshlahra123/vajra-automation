"""One-off probe: which models exist, and do TTS + music work."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import gem

os.makedirs("out", exist_ok=True)
names = gem.list_models()
print("models:", ", ".join(n.replace("models/", "") for n in names if any(k in n for k in ("flash", "pro", "tts", "lyria", "omni", "banana"))))

for m in ("gemini-3.8-flash", "gemini-flash-latest"):
    try:
        print("text", m, "->", gem.text(m, "Reply with exactly: OK").strip()[:40]); break
    except Exception as e:
        print("text", m, "FAIL", str(e)[:300])

vo = "Har paanch slab pe naya ply? Ab nahi. VAJRA PP shuttering sheet, ek haath se utha lo, chaalis baar chalao."
for voice in ("Charon", "Puck"):
    try:
        r = gem.interact("gemini-3.8-flash-tts",
                         [{"type": "user_input", "content": [{"type": "text", "text": vo,
                           "annotations": [{"type": "speech_metadata", "style": "confident Indian male, Hinglish, energetic but natural, like a contractor talking to a friend"}]}]}],
                         response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": voice}]})
        print("tts", voice, gem.save_first(r, "audio", f"out/vo-{voice}.wav"), "usage", json.dumps(r.get("usage", {}))[:200])
    except Exception as e:
        print("tts", voice, "FAIL", str(e)[:400])

for m in ("lyria-3.5", "lyria-3-clip-preview"):
    try:
        r = gem.interact(m, "30 second upbeat Indian instrumental background track for a construction product reel, dhol and modern beat, no vocals, energetic",
                         response_format={"type": "audio"})
        print("music", m, gem.save_first(r, "audio", f"out/music-{m}.mp3"), "usage", json.dumps(r.get("usage", {}))[:200]); break
    except Exception as e:
        print("music", m, "FAIL", str(e)[:400])
