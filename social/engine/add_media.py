"""UNIFIED media library: everything from Telegram goes through here.

Photos, videos, voice - everything lands in social/inbox/ first, then gets processed:
- AI check (Flow AI vs real phone photo/video)
- Quality check (no dirty sheets, blur, text/prices for photos)
- Copied to final location (assets/photos/ or assets/clips/)
- Registered in ONE library: social/library.json

Usage:
  python social/engine/add_media.py                    process all new inbox items
  python social/engine/add_media.py --accept-all       skip rejection checks (owner approved)
  python social/engine/add_media.py --files file1,file2  process specific files only

Library format (social/library.json):
{
  "media-id": {
    "type": "photo"|"video"|"voice",
    "path": "assets/photos/in-20261113.jpg",  # final location
    "inbox": "20261113-100530-MrBeast.jpg",   # original inbox filename
    "desc": "smooth concrete column finish",
    "ai": true|false,
    "ok": true|false,   # false = rejected (dirty/blur/etc)
    "reject_reason": "...",  # only if ok=false
    "who": "MrBeast"|"Rahul"|"owner",
    "added": "2026-11-13",
    "secs": 7.9  # video/voice only
  }
}
"""
import argparse, datetime, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

INBOX = os.path.join(ROOT, "social", "inbox")
LIBRARY = os.path.join(ROOT, "social", "library.json")
PHOTOS_DIR = os.path.join(ROOT, "assets", "photos")
CLIPS_DIR = os.path.join(ROOT, "assets", "clips")


def load_library():
    """Load the unified library."""
    if os.path.exists(LIBRARY):
        return json.load(open(LIBRARY, encoding="utf-8"))
    return {}


def save_library(lib):
    """Save the unified library."""
    with open(LIBRARY, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)


def process_photo(inbox_file, accept_all=False):
    """Process a photo from inbox."""
    import gem
    
    path = os.path.join(INBOX, inbox_file)
    ok, desc, ai = True, "VAJRA PP shuttering site photo", False
    reject_reason = ""
    
    if not accept_all:
        try:
            q = ("This photo was sent by the owners of VAJRA (grey PP hollow shuttering sheets) for Instagram reels/posts. "
                 "JSON only: {\"ok\": true/false, \"ai\": true/false, \"desc\": \"one line: what it shows (column/slab/beam/stock/cutting...)\", \"why\": \"\"}. "
                 "ai=true if it looks AI-generated (Gemini/Flow image) rather than a real phone photo; if unsure, ai=true. "
                 "ok=false if: the sheet looks dirty/used/stained with old concrete, it is blurry or very dark, a price or readable text is "
                 "prominent, or a close-up face is the main subject.")
            r = gem.interact("gemini-3.5-flash-lite", [{"type": "text", "text": q}, gem.img_part(path)],
                             response_format={"type": "text", "mime_type": "application/json"})
            j = json.loads("".join(v for k, _, v in gem.outputs(r) if k == "text"))
            ok, desc, ai = bool(j.get("ok")), (j.get("desc") or desc)[:140], bool(j.get("ai"))
            if not ok:
                reject_reason = j.get("why", "")[:100]
        except Exception as e:
            print(f"Check failed for {inbox_file}, adding anyway:", str(e)[:100])
            ok = True
    
    # Generate media ID
    stamp = inbox_file.split("-")[0]  # e.g., "20261113"
    media_id = f"ph-{stamp}-{os.urandom(4).hex()}"
    
    # Copy to final location if OK
    final_path = None
    if ok:
        final_filename = f"in-{stamp}.jpg"
        final_path = os.path.join(PHOTOS_DIR, final_filename)
        # Make unique if exists
        counter = 1
        while os.path.exists(final_path):
            final_filename = f"in-{stamp}-{counter}.jpg"
            final_path = os.path.join(PHOTOS_DIR, final_filename)
            counter += 1
        shutil.copy(path, final_path)
        final_path = f"assets/photos/{final_filename}"
    
    # Extract who from filename
    who = "owner"
    if "-MrBeast" in inbox_file:
        who = "MrBeast"
    elif "-Rahul" in inbox_file:
        who = "Rahul"
    
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    entry = {
        "type": "photo",
        "path": final_path if ok else None,
        "inbox": inbox_file,
        "desc": ("AI image: " if ai else "REAL photo: ") + desc,
        "ai": ai,
        "ok": ok,
        "who": who,
        "added": now.strftime("%Y-%m-%d")
    }
    
    if not ok:
        entry["reject_reason"] = reject_reason
    
    return media_id, entry, ok


def process_video(inbox_file, accept_all=False):
    """Process a video from inbox."""
    import ai_check
    from make_reel import dur
    
    path = os.path.join(INBOX, inbox_file)
    
    # AI check
    ai, desc = ai_check.check(path)
    
    # Generate media ID
    stamp = inbox_file.split("-")[0]  # e.g., "20261113"
    media_id = f"cl-{stamp}-{os.urandom(4).hex()}"
    
    # Copy to final location
    final_filename = f"tg-{stamp}-{os.urandom(4).hex()}.mp4"
    final_path = os.path.join(CLIPS_DIR, final_filename)
    shutil.copy(path, final_path)
    
    # Extract who from filename
    who = "owner"
    if "-MrBeast" in inbox_file:
        who = "MrBeast"
    elif "-Rahul" in inbox_file:
        who = "Rahul"
    
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    entry = {
        "type": "video",
        "path": f"assets/clips/{final_filename}",
        "inbox": inbox_file,
        "desc": ("AI video: " if ai else "REAL video: ") + desc,
        "ai": ai,
        "ok": True,  # videos always accepted
        "who": who,
        "added": now.strftime("%Y-%m-%d"),
        "secs": round(dur(final_path), 1)
    }
    
    return media_id, entry, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept-all", action="store_true", help="Skip rejection checks")
    ap.add_argument("--files", help="Process specific files (comma-separated)")
    args = ap.parse_args()
    
    lib = load_library()
    
    # Get already processed files
    processed_inbox = {item["inbox"] for item in lib.values() if isinstance(item, dict) and "inbox" in item}
    
    # Get inbox files to process
    if args.files:
        inbox_files = [f.strip() for f in args.files.split(",")]
    else:
        if not os.path.isdir(INBOX):
            print(f"Inbox directory not found: {INBOX}")
            return
        inbox_files = sorted(os.listdir(INBOX))
    
    added, rejected = 0, 0
    
    for filename in inbox_files:
        # Skip already processed
        if filename in processed_inbox:
            continue
        
        # Skip .txt files
        if filename.endswith(".txt"):
            continue
        
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            if ext in [".jpg", ".jpeg", ".png"]:
                media_id, entry, ok = process_photo(filename, args.accept_all)
                lib[media_id] = entry
                if ok:
                    print(f"✅ ADDED photo: {media_id} - {entry['desc'][:60]}")
                    added += 1
                else:
                    print(f"❌ REJECTED photo: {media_id} - {entry.get('reject_reason', 'failed checks')}")
                    rejected += 1
                    
            elif ext in [".mp4", ".mov", ".avi"]:
                media_id, entry, ok = process_video(filename, args.accept_all)
                lib[media_id] = entry
                print(f"✅ ADDED video: {media_id} - {entry['desc'][:60]}")
                added += 1
                
            else:
                print(f"⚠️  SKIPPED unknown type: {filename}")
                
        except Exception as e:
            print(f"❌ ERROR processing {filename}: {str(e)[:200]}")
    
    save_library(lib)
    
    print(f"\n{'='*60}")
    print(f"DONE: {added} added, {rejected} rejected")
    print(f"Library: {LIBRARY}")
    
    # Output for GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"added={added}\n")
            f.write(f"rejected={rejected}\n")


def get_photos():
    """Get all accepted photos for use in reels/stories."""
    lib = load_library()
    return {
        media_id: item["desc"]
        for media_id, item in lib.items()
        if item.get("type") == "photo" and item.get("ok") and item.get("path")
    }


def get_videos():
    """Get all videos for use in reels."""
    lib = load_library()
    return {
        media_id: item
        for media_id, item in lib.items()
        if item.get("type") == "video" and item.get("ok") and item.get("path")
    }


if __name__ == "__main__":
    main()
