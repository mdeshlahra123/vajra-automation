import sys, os
sys.path.insert(0, "social/engine")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "x"); os.environ.setdefault("TELEGRAM_CHAT_ID", "x")
import long_video as L
print("RESULT", L.ig_long("social/tmp/iglong.mp4", "release test (not published)", publish=False), flush=True)