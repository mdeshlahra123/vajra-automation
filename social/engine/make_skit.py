"""Make a complete skit reel from 3 Flow videos + end card.

Owner sends 3 Flow videos to Telegram (the 3 parts of a skit), this:
1. Downloads all 3 videos
2. Joins them in sequence
3. Adds the brand end card (cta-card.mp4)
4. Creates a pending item for approval

Usage:
  python social/engine/make_skit.py --clips file_id1,file_id2,file_id3 --title "Labour ke liye halka"

Env: TELEGRAM_BOT_TOKEN, GEMINI_API_KEY (for caption generation)
"""
import argparse, datetime, json, os, subprocess, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem
from make_reel import A, sh

TG = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', '')}/"


def download(file_id, path):
    """Download video from Telegram."""
    info = json.load(urllib.request.urlopen(TG + "getFile?file_id=" + file_id, timeout=60))
    if not info.get("ok"):
        raise RuntimeError(f"getFile failed: {info}")
    fp = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{fp}"
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())
    print(f"Downloaded {os.path.basename(path)}")


def join_videos(parts, end_card, output):
    """Join skit parts + end card with ffmpeg."""
    # Create concat file
    concat_file = output.replace(".mp4", ".txt")
    with open(concat_file, "w") as f:
        for part in parts:
            f.write(f"file '{os.path.abspath(part)}'\n")
        f.write(f"file '{os.path.abspath(end_card)}'\n")
    
    # Join with ffmpeg (concat demuxer - fastest, no re-encoding)
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy",  # copy streams, no re-encode
        output
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Joined {len(parts)} parts + end card → {os.path.basename(output)}")
    except subprocess.CalledProcessError as e:
        # If concat fails (different codecs), fall back to re-encode
        print("Concat failed, re-encoding...")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Joined (re-encoded) {len(parts)} parts + end card → {os.path.basename(output)}")
    
    os.remove(concat_file)


def generate_caption(title):
    """Generate Instagram caption for the skit."""
    prompt = f"""Write an Instagram caption for this VAJRA PP shuttering reel: "{title}"

It's a dialogue skit (contractor/labour/engineer talking). Caption must:
- Start with a hook line about the skit topic (problem: ply cost/weight/breaking)
- Mention the skit characters (contractor, labour, engineer)
- End with hashtags: #PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai

Keep it 2-3 lines, Hinglish, casual, relatable.
Return plain text only, no explanations."""
    
    try:
        return gem.text("gemini-3.5-flash-lite", prompt).strip()
    except Exception as e:
        print(f"Caption generation failed: {e}")
        # Fallback caption
        return f"{title}\n\n#PPFormwork #PlasticShuttering #Shuttering #Formwork #Construction #Contractors #Builders #Chhattisgarh #Raipur #Durg #Bhilai"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="3 Telegram file_ids (comma-separated)")
    ap.add_argument("--title", required=True, help="Skit title (e.g., 'Labour ke liye halka')")
    ap.add_argument("--who", default="owner", help="Who sent the clips")
    args = ap.parse_args()
    
    clips = [c.strip() for c in args.clips.split(",") if c.strip()]
    if len(clips) != 3:
        sys.exit(f"ERROR: Need exactly 3 clips, got {len(clips)}")
    
    # Setup paths
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%m%d-%H%M")
    skit_id = f"skit-{stamp}"
    media_dir = A("social", "media")
    os.makedirs(media_dir, exist_ok=True)
    
    # Download all 3 parts
    parts = []
    for i, fid in enumerate(clips, 1):
        part_path = os.path.join(media_dir, f"{skit_id}-part{i}.mp4")
        download(fid, part_path)
        parts.append(part_path)
    
    # Join parts + end card
    end_card = A("assets", "brand", "cta-card.mp4")
    output = os.path.join(media_dir, f"{skit_id}.mp4")
    join_videos(parts, end_card, output)
    
    # Generate caption
    caption_text = generate_caption(args.title)
    caption_file = A("social", "captions", f"{skit_id}.txt")
    os.makedirs(os.path.dirname(caption_file), exist_ok=True)
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(caption_text)
    print(f"✅ Caption saved: {os.path.basename(caption_file)}")
    
    # Add to pending for approval
    pending_path = A("social", "pending.json")
    pending = json.load(open(pending_path, encoding="utf-8")) if os.path.exists(pending_path) else {"items": []}
    
    pending["items"].append({
        "id": skit_id,
        "file": f"social/media/{skit_id}.mp4",
        "caption": f"captions/{skit_id}.txt",
        "title": f"Skit: {args.title}",
        "position": "end",
        "status": "draft",
        "by": args.who,
        "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "ai": False,  # dialogue videos, not AI-generated content
        "skit": True
    })
    
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ DONE: {skit_id}")
    print(f"Video: {output}")
    print(f"Caption: {caption_file}")
    print(f"\nNext: python social/tg.py send {skit_id}")
    
    # Clean up temp parts
    for part in parts:
        os.remove(part)
    print("Cleaned up temp files")


if __name__ == "__main__":
    main()
