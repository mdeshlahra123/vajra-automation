# VAJRA automation

Runs VAJRA Formwork's Instagram, Facebook, ads and Telegram bot on GitHub, free, with the laptop off.

## What runs when (IST)

| Time | What | Started by |
|---|---|---|
| 07:00 | Brain: checks posts and ads, makes one improvement, reports on Telegram (Monday = weekly report) | cron-job.org, `agent.yml` |
| 08:30 | Ads manager: pauses weak ads, resumes good ones, never changes budgets | cron-job.org, `ads.yml` |
| 09:30 | Morning reel + Story (also Facebook). Before it: website update, covers, silent-reel check | cron-job.org, `post.yml` |
| 10:00 Mon/Wed/Fri | AI reel plan sent to Telegram (nothing is made until someone taps Banao) | cron-job.org, `make-reel.yml` |
| 19:30 | Evening photo / carousel + Story | cron-job.org, `post.yml` |

## Telegram group "Vajra Approvals"

- `/ask <question>` — the bot answers in ~30 s (can also move the queue and remember rules). Replying to a bot message works too.
- Send **videos** — clips become a reel (20 min after the last clip, or type `/reel`).
- Send **photos** — saved to `social/inbox/` for posts.
- Buttons: ✅ Approve / ❌ Reject a finished reel; ▶️ Banao / reply-to-change on an AI reel plan.

## Where things are

| Path | What |
|---|---|
| `social/queue.json` | What posts next. `posts` (in order), `hold` (not ready), `stories` (scheduled Stories) |
| `social/captions/` | Captions of upcoming posts (`posted/` = old ones) |
| `social/daily-post.ps1` | Posts to Instagram + Facebook + Story |
| `social/publish_site.py` | Daily website upload/cleanup, covers, silent-reel check |
| `social/tg.py`, `social/apps-script/` | Telegram approvals bot |
| `social/agent/` | Brain tools (`tools.py`), quick answers (`quick.py`) |
| `social/engine/` | Reel makers (AI, real clips, voice), covers, brand rules `brand.md`, claim guard `claims.py` |
| `social/ads_manager.py` | Daily ads rules |
| `GEMINI.md`, `agent/memory.md` | Brain rules and memory |
| `assets/` | Brand files and approved photos |
| `archive/` | Old one-time setup packs |

## Rules everything follows

No money spent beyond the ₹100/day ad budget · no sheet price in reels · never a number of uses (only "sahi handling ke saath ply se 2-3 guna zyada chalti hai") · never a reel without sound · problem scenes show brown ply, never the grey sheet · no dirty/used sheet or slab-ceiling photos.

Videos and images are served from the website repo (`vajraformwork.vercel.app/social/`), which is cleaned daily.
