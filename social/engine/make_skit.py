"""Make a finished skit reel: 3 Flow dialogue clips (parts 1-2-3, their own speech kept) + the brand end card.

  python social/engine/make_skit.py --files assets/clips/a.mp4,assets/clips/b.mp4,assets/clips/c.mp4 --title "..."
  python social/engine/make_skit.py --clips <tg_file_id>,<id>,<id> --title "..."   (download from Telegram first)

All parts are scaled/padded to 1080x1920, 30 fps, 48 kHz stereo (Flow clips are 464x848 / 44.1 kHz, the end card is
1080x1920 / 48 kHz, so a stream-copy join would break). Clips without sound get silence. Caption by Gemini (free key)
through the claim guard. Audio check (max_volume > -60 dB) before it goes anywhere. Adds a pending item
(ai=True: Flow clips are AI, Instagram AI label) and prints SKIT_ID=<id>; send with: python social/tg.py send <id>
"""
import argparse, datetime, json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
END_CARD = os.path.join(ROOT, "assets", "brand", "cta-card.mp4")
# owner 13 Nov: the end card needs the voiceover too (same line + Charon voice as the other reels).
# Made once with Gemini TTS and kept in the repo, so every skit reuses it.
END_VO_LINE = "Comment mein PP likhiye, follow kijiye, rate aapke DM mein."
END_VO = os.path.join(ROOT, "assets", "brand", "cta-vo.wav")


def end_vo():
    if not os.path.exists(END_VO):
        from make_reel import tts
        tts(END_VO_LINE, END_VO)
    return END_VO
TAGS = "#PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai"


def download(file_id, path):
    tg = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/"
    info = json.load(urllib.request.urlopen(tg + "getFile?file_id=" + file_id, timeout=60))
    if not info.get("ok"):
        raise RuntimeError(f"getFile failed (bots can only download up to 20 MB): {info}")
    url = f"https://api.telegram.org/file/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{info['result']['file_path']}"
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())


def has_audio(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())


def join(parts, out, vo=None):
    """parts + end card -> one 1080x1920 30 fps reel, each part's own sound kept; end card carries the voiceover."""
    files = parts + [END_CARD]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f in files:
        cmd += ["-i", f]
    flt, n = [], len(files)
    if vo:
        cmd += ["-i", vo]
        card_len = max(dur(END_CARD), dur(vo) + 0.5)   # card held (last frame) until the voice ends
    for i, f in enumerate(files):
        if vo and i == n - 1:   # end card: clone last frame to fit the voice, voice starts 0.2 s in
            flt.append(f"[{i}:v]scale=1080:1920,tpad=stop_mode=clone:stop_duration=10,trim=0:{card_len:.3f},setpts=PTS-STARTPTS,"
                       f"fps=30,setsar=1,format=yuv420p[v{i}]")
            flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=200|200,apad,atrim=0:{card_len:.3f}[a{i}]")
            continue
        # fit the clip, fill the rest with a blurred zoomed copy of itself (no black bars if Flow made 16:9)
        flt.append(f"[{i}:v]split[f{i}][b{i}];"
                   f"[b{i}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.08[bg{i}];"
                   f"[f{i}]scale=1080:1920:force_original_aspect_ratio=decrease[fg{i}];"
                   f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1,format=yuv420p[v{i}]")
        if has_audio(f):
            flt.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
        else:   # silent track as long as the clip
            flt.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{dur(f):.3f}[a{i}]")
    flt.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    cmd += ["-filter_complex", ";".join(flt), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip() or 0)


def max_volume(p):
    err = subprocess.run(["ffmpeg", "-i", p, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", err)
    return float(m.group(1)) if m else -99.0


def caption(title, hook=""):
    import claims
    text = ""
    try:
        import gem
        text = gem.text("gemini-3.5-flash-lite", f"""Write an Instagram caption in casual Hinglish for a short VAJRA PP shuttering
reel: "{title}" (hook idea: {hook}). Talking characters or site people teach one lesson.
2-3 short lines, first line a hook. Last line: "Follow kijiye, comment mein likhiye PP".
Never give a number of uses, never a price, never the words waterproof/paani/barish. No hashtags. Plain text only.""").strip()
    except Exception as e:
        print("caption by Gemini failed:", str(e)[:120])
    text = claims.fix_caption(text) if text else f"{title}\nFollow kijiye, comment mein likhiye PP"
    return text.strip() + "\n\n" + TAGS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", help="3 clip paths (repo-relative), parts 1,2,3 in order")
    ap.add_argument("--clips", help="3 Telegram file_ids, parts 1,2,3 in order")
    ap.add_argument("--title", required=True)
    ap.add_argument("--who", default="owner")
    ap.add_argument("--hook", default="")
    a = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    sid = "skit-" + now.strftime("%m%d-%H%M")
    media = os.path.join(ROOT, "social", "media"); os.makedirs(media, exist_ok=True)
    k = 1
    while os.path.exists(os.path.join(media, sid + ".mp4")):   # several episodes built in the same minute
        k += 1; sid = "skit-" + now.strftime("%m%d-%H%M") + f"-{k}"
    if a.files:
        parts = [os.path.join(ROOT, f.strip()) for f in a.files.split(",") if f.strip()]
    else:
        parts = []
        for i, fid in enumerate((c.strip() for c in (a.clips or "").split(",") if c.strip()), 1):
            p = os.path.join(media, f"{sid}-part{i}.mp4"); download(fid, p); parts.append(p)
    if not 2 <= len(parts) <= 12:
        sys.exit(f"need 2-12 parts, got {len(parts)}")
    out = os.path.join(media, sid + ".mp4")
    try:
        vo = end_vo()
    except Exception as e:   # no voice possible right now: still build, but say so on the approval card
        print("END VO FAILED, end card without voice:", str(e)[:150]); vo = None
    join(parts, out, vo)
    mv = max_volume(out)
    if mv <= -60:
        sys.exit(f"NO AUDIO (max_volume {mv} dB): not sent (owner rule: never queue a reel without sound)")
    capf = os.path.join(ROOT, "social", "captions", sid + ".txt")
    open(capf, "w", encoding="utf-8").write(caption(a.title, a.hook))
    pend_p = os.path.join(ROOT, "social", "pending.json")
    pend = json.load(open(pend_p, encoding="utf-8")) if os.path.exists(pend_p) else {"items": []}
    pend["items"].append({"id": sid, "file": f"social/media/{sid}.mp4", "caption": f"captions/{sid}.txt",
                          "title": f"🗣️ Skit: {a.title} ({dur(out):.0f}s, end card {'with voice' if vo else 'WITHOUT voice'})", "position": "end", "status": "draft",
                          "by": a.who, "at": now.strftime("%Y-%m-%d %H:%M"), "ai": True, "skit": True})
    json.dump(pend, open(pend_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if not a.files:   # downloaded copies only; library clips are never deleted
        for p in parts:
            os.remove(p)
    print(f"built {out} ({dur(out):.1f}s, max_volume {mv} dB)")
    print("SKIT_ID=" + sid)


if __name__ == "__main__":
    main()
