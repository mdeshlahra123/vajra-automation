"""Migrate existing split libraries into the unified social/library.json

Combines:
- assets/photos/library.json → photo entries
- assets/clips/library.json → video entries

Into: social/library.json with unified format
"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

OLD_PHOTOS = os.path.join(ROOT, "assets", "photos", "library.json")
OLD_CLIPS = os.path.join(ROOT, "assets", "clips", "library.json")
NEW_LIBRARY = os.path.join(ROOT, "social", "library.json")


def main():
    unified = {}
    
    # Migrate photos
    if os.path.exists(OLD_PHOTOS):
        print(f"Migrating photos from {OLD_PHOTOS}...")
        old_photos = json.load(open(OLD_PHOTOS, encoding="utf-8"))
        
        for key, item in old_photos.items():
            if not isinstance(item, dict):
                continue
                
            # Convert old format to new format
            media_id = f"ph-{key}"
            
            # Determine path
            path = None
            if item.get("ok") and key.startswith("in-"):
                # New inbox photos
                path = f"assets/photos/{key}.jpg"
            elif item.get("ok"):
                # Old photos (no "in-" prefix)
                path = f"assets/photos/{key}.jpg"
            
            unified[media_id] = {
                "type": "photo",
                "path": path,
                "inbox": item.get("src", ""),
                "desc": item.get("desc", "VAJRA photo"),
                "ai": item.get("ai", False),
                "ok": item.get("ok", True),
                "who": "owner",
                "added": "2026-10-26"  # approximate date for old items
            }
            
            if not item.get("ok"):
                unified[media_id]["reject_reason"] = "failed quality check"
        
        print(f"  ✅ Migrated {len(old_photos)} photo entries")
    
    # Migrate videos
    if os.path.exists(OLD_CLIPS):
        print(f"Migrating videos from {OLD_CLIPS}...")
        old_clips = json.load(open(OLD_CLIPS, encoding="utf-8"))
        
        for filename, item in old_clips.items():
            if not isinstance(item, dict):
                continue
            
            # Convert old format to new format
            media_id = f"cl-{filename.replace('.mp4', '')}"
            
            unified[media_id] = {
                "type": "video",
                "path": f"assets/clips/{filename}",
                "inbox": "",  # clips went straight to assets, no inbox
                "desc": item.get("note", "construction video"),
                "ai": item.get("flow", False),
                "ok": True,  # all clips were accepted
                "who": item.get("who", "owner"),
                "added": item.get("added", "2026-10-26"),
                "secs": item.get("secs", 7.9)
            }
        
        print(f"  ✅ Migrated {len(old_clips)} video entries")
    
    # Save unified library
    print(f"\nSaving unified library to {NEW_LIBRARY}...")
    with open(NEW_LIBRARY, "w", encoding="utf-8") as f:
        json.dump(unified, f, ensure_ascii=False, indent=2)
    
    print(f"✅ DONE: {len(unified)} total media items in unified library")
    print(f"\nNext steps:")
    print(f"1. Update make_reel.py, make_real.py, story.py to use the new library")
    print(f"2. Update GitHub workflows to use add_media.py instead of add_photo.py + save_clips.py")
    print(f"3. Test the new system")
    print(f"4. Backup and remove old libraries once confirmed working")


if __name__ == "__main__":
    main()
