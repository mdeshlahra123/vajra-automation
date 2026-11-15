"""A3: 'Shuttering Ki Duniya' episodes made fully automatically on Muse (no Flow, no owner clicks).

One episode = one batch in the drop repo:
  job 0 (image): the episode's cast standing together on its fixed set (3D cartoon, 9:16) = the look reference
  jobs 1-3 (video): 10 s clips that all START from that image, so characters and set stay the same in every clip
The fixed character looks, sets and topic list come from series.py. Script text via OmniRoute (gen_plan.llm).
Called by gen_plan.py when it decides the next batch is an episode.
"""
import os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import series

LOOK = ("High-quality 3D animated cartoon in a Pixar-like style, vertical 9:16, warm golden light, expressive faces with "
        "big eyes, construction objects that are alive and talk. No humans. No text, letters, logos, name tags or subtitles.")

PROMPT = """Write ONE episode of "Shuttering Ki Duniya", a Hindi 3D-cartoon Instagram series for VAJRA (plain light-grey
hollow PP plastic shuttering sheets, Chhattisgarh). Construction objects with faces talk and teach one useful, correct lesson.
Topic: {topic}
Cast (exactly these, all present in every part): {cast}
Write exactly 3 parts of 10 seconds each: part 1 = the hook (a mistake or shock in the first 2 seconds), part 2 = why it goes
wrong, part 3 = the right way + the character says "Follow karo Shuttering Ki Duniya".
For each part: "speaker" (one cast id), "line" (what that character says: simple spoken Hinglish in Latin letters, max 11 words),
"action" (what everyone does, 1 sentence, no dialogue in it).
Rules (any break = rejected):
- Never a number of uses/times, never a price, never how fast ply breaks. Allowed only: "ply se 2-3 guna zyada chalti hai".
- Structural numbers (days, spacing, overlap, mm): say "engineer se confirm karein" instead of a number.
- No words: waterproof, paani, barish, rain, phool. VAJRA appears only if natural (not every episode sells).
Also "title" (short Hinglish) and "hook" (caption first line, max 9 words).
JSON only: {{"title":"","hook":"","parts":[{{"speaker":"","line":"","action":""}},{{"speaker":"","line":"","action":""}},{{"speaker":"","line":"","action":""}}]}}"""

NAMES = {"ply": "PLY BHAIYA", "vajra": "VAJRA SHEET", "balli": "BALLI", "sariya": "SARIYA USTAD", "chhotu": "CHHOTU", "mami": "CONCRETE MAMI"}


def cast_for(topic):
    """2-3 characters that fit the topic; Ply Bhaiya + VAJRA Sheet often, others by keyword."""
    t = topic.lower(); c = ["ply"]
    for k, words in (("balli", ("balli", "prop", "slab")), ("sariya", ("sariya", "overlap", "cage", "cover")),
                     ("chhotu", ("cover block",)), ("mami", ("concrete", "honeycomb", "vibrat", "paani", "set"))):
        if any(w in t for w in words) and len(c) < 3:
            c.append(k)
    if len(c) < 3:
        c.append("vajra")
    return c[:3]


def plan_episode(used_topics, llm, problems):
    topics = sorted([t for t in series.TOPICS if not re.search(r"paani|barish|rain|phool", t, re.I)],
                    key=lambda t: (used_topics.get(t, "0000"), random.random()))
    topic = topics[0]; cast = cast_for(topic)
    setting = random.choice(series.SETS)
    extra = ""
    for _ in range(3):
        try:
            r = llm(PROMPT.format(topic=topic, cast=", ".join(f"{k} ({NAMES[k]})" for k in cast)) + extra) or {}
        except Exception as e:
            print("episode model failed:", str(e)[:120]); r = {}
        parts = [p for p in r.get("parts", []) if p.get("line") and p.get("action") and p.get("speaker") in cast][:3]
        bad = problems(str(r))
        if len(parts) == 3 and not bad and r.get("hook"):
            return {"kind": "series", "topic": topic, "cast": cast, "setting": setting,
                    "title": r.get("title", topic)[:70], "hook": r["hook"][:90], "parts": parts}
        extra = f"\n\nYour last answer broke the rules ({', '.join(bad) or 'need 3 parts, speakers from the cast, hook'}). Rewrite."
    return None


def image_prompt(ep):
    looks = " ".join(series.CHARS[c] for c in ep["cast"])
    return (f"{LOOK} {ep['setting']} The characters stand together in this set, all clearly visible, facing the camera, "
            f"ready to talk: {looks}")


def video_prompt(ep, part, i):
    looks = " ".join(series.CHARS[c] for c in ep["cast"])
    lead = "Start exactly from this image." if i == 0 else "Start exactly from this image (same set, same characters, same looks)."
    return (f"{LOOK} {lead} 10 seconds, the camera stays in this set. Characters, all visible together: {looks} "
            f"Action: {part['action']} {NAMES[part['speaker']]} says \"{part['line']}\" in clear Hindi with a matching moving mouth. "
            "Sound: only that line, light site ambience, soft playful background music. Do NOT add subtitles or any on-screen text.")
