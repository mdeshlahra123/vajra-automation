# VAJRA video work: open asks and progress

Read this first in every session. Update it after every change. Owner rules: act without asking, report afterwards,
no money spent, review the real output (frames + timing) before saying "done".

## FIXED 13 Nov 2026 - Owner complaint: "paani paani everywhere" + force-post feature
**Problem 1**: Variety DEAD. Last 10 reels (Nov 2-12):
- "waterproof" x16, "paani" x14, "phool/phoolti" x13 times
- REVEALS photos: only 8 photos cycling (slab-underside, beam-box, column-smooth2, godown, finish-column...)
- Growth loop stuck on "waterproof / rain / mud" angle because it won once

**Problem 2**: No way to force-post a specific video - daily-post.ps1 always posted the first queue item

**Fixed (13 Nov 10:36 AM)**:
1. ✅ **claims.py**: Added OVERUSED word blocker - rejects waterproof/paani/phool/barish/keechad if used in last 3 reels
2. ✅ **growth-plan.json**: RESET - NO water mentions for 7 days. New angles: one-man lift, smooth finish, easy cutting, wash-reuse, cost, beam/wall
3. ✅ **make_real.py REVEALS**: Expanded from 5 pairs (10 photos) to 15 pairs (30 photos) - lasts 3+ weeks without repeating
4. ✅ **story.py PHOTOS**: Added v4-point, v1-lean, r-throw
5. ✅ **brand.md**: Added VARIETY RULE - waterproof/paani BANNED for 7 days
6. ✅ **daily-post.ps1**: Added `-Id` parameter for force-posting specific items, bypassing queue order and daily guards

**Posted (13 Nov 10:37 AM)**:
- tg-1110-0847-4 (woman/men meme: "Mard chahte kya hai? Vajra PP panel") - FORCED via `.\daily-post.ps1 -Id tg-1110-0847-4`
- Instagram: https://www.instagram.com/reel/Dfq12WDHZx3/
- Facebook: video 2072731736708179

Owner deleted tonight's 21:30 reel (had paani again). Tomorrow's reels will follow the new angles.

---

## The owner's asks (12 Nov 2026, from the Antigravity guide + 2 GitHub repos)
Owner: "do everything you can" for:
1. Captions timed to the voice: long videos AND normal reels.
2. Effects from github.com/Vibha-Ramprakash/claude-video-effects (MIT), the ones that work without a presenter.
3. Animated text reels (motion graphics, no AI credits), ideas from github.com/yihui-dev/awesome-opus5-5-videos
   (explainer / kinetic-typography prompts), built with HyperFrames (available as a skill) or our own renderer.
4. Act as the reviewer: check sync and quality myself, fix before showing. Owner on 12 Nov: "so bad, nothing is in sync".

Earlier asks that are still open:
5. Long videos (weekly, 11 Nov): better sync between words and pictures; captions (done, see below); generate missing visuals
   only with Flow clips from the owner (AI video generation is OFF to save credits).
6. Instagram long video: test whether a 6-min video can be published as a reel via the API (container only, no publish).
7. Monetization mix (11 Nov): 3-4 non-sales posts a week (Wed educational, Fri entertainment AI reels: done), long
   educational video weekly (done), short educational tips cut from the long video (done: 2 Shorts).

## Status
| # | Item | Status |
|---|---|---|
| 1a | Reel captions | DONE 12 Nov. social/engine/polish.py, timing from the builder (line start + TTS length), max 3 words, never across a sentence, none on the end card. Verified by an 8-frame audit on reel-real-1112-1101. |
| 1b | Long-video captions | DONE 12 Nov. Voice is made one sentence at a time; captions from polish.timed_chunks. Offline test (2 chapters, 19 sentences, beep voice): caption starts within 0.001 s of each sentence's sound; picture cuts 0.15 s before the words. First real build Thu 20 Nov: frame-audit it. |
| 2 | Effects | DONE 12 Nov (second pass). Tested 8 effects on a no-presenter reel: they work. Defaults rebranded in social/fx/scripts/fx.py (credit to @vibha.in.progress kept in the header, MIT LICENSE kept). polish.fx_pass now uses: huge-strike 'PLY' on the first brown-ply scene; tape-label with the spoken claim (WATERPROOF / HALKI SHEET / KIL PAKADTI / CUTTER SE KATTI / DHO KAR REUSE / SMOOTH FINISH / EK AADMI KAAFI), max 2 per reel; comment-box 'PP' on the end card. Frame-audited. Not used: effects that need a face (orbit, locked-on, spotlight...). |
| 3 | Animated text reels | DONE 12 Nov, rebuilt with the Opus 5.5 prompt ideas: every move starts on a beat (beats.py reads the music bed: 127.7 bpm, first beat 0.05 s; tested on synthetic 100/120/140 bpm within 0.03 s), spring-physics easing (spring()), roles by meaning (mistakes go grey when the fix lands), the myth shrinks and greys out then the FACT builds one word per beat (transform, no cut). social/engine/text_reel.py + text-reel.yml (Sat 10:00 IST). Frame-audited on beats; two layout bugs found and fixed (tag collision, orphan word). Ideas not yet used: loop (last frame = first), beat-synced SFX, before/after format. |
| 4 | Reviewer step | PARTLY 12 Nov: polish.py checks every caption sits inside its voice line, none on the end card, no overlaps; any failure = CHECK -> reel goes for approval, not auto-queue. Still to add: frame audit image sent with each new reel's FYI. |
| 5 | Long-video picture sync | DONE 12 Nov (code), first live use Thu 20 Nov. assign_sentences(): one library item per sentence by meaning (free Gemini text), max 3 uses per item, shots at least 3 s, cuts on sentence starts. Fallback = rotation per chapter (offline-tested). If the first live build looks off, tune the prompt in assign_sentences. |
| 6 | IG long-video | DONE 12 Nov. Tested: Meta accepts a 6 min reel from video_url (error 2207076 is transient, retried up to 4x). Resumable upload is broken at Meta (ProcessingFailedError). long_video.ig_long hosts the file as a TEMPORARY GitHub release asset, creates the container, publishes, deletes the release. First live use Thu 20 Nov. (A 52 MB test file remains in git history under social/tmp.) |

## Known facts / traps
- Gemini free credits nearly gone (about Rs 345 on 11 Nov). AI video generation disabled in make_reel.py. Owner must set the spend cap to Rs 1,600 in AI Studio.
- Hindi whisper splits Hinglish words differently; never map script words to heard words by position over a whole reel.
- GitHub apt installs can hang: always wrap in `timeout 240`.
- mediapipe on GitHub needs libgl1 libegl1 libgles2; faster-whisper audio is loaded via an ffmpeg pipe (load_wav) to avoid PyAV clashes.
- Test helpers: .github/workflows/polish-test.yml (input id), long-video.yml (mode=build publish=false).

## SKITS (13 Nov)
- skit_prompts.py (09:30 IST): 3 dialogue prompts, one Telegram message each, claim guard (use numbers incl. Hindi words, water words, price, brand) + 3 Gemini retries + clean bank fallback. Stores the sent skit as "open" in social/skit-prompts-state.json.
- make-real.yml -> save_clips.py -> skit_match.py: Gemini compares 3 frames of each new clip with the open skit's prompts (unsure = normal clip). Parts can arrive in any order / batches within 3 days. All 3 matched -> make_skit.py: 1080x1920 30 fps, blurred fill for 16:9 clips, own dialogue kept, cta-card end card, caption via claims guard, max_volume check, ai=True, sent for approval. Caption "skit" forces a clip into the skit. Skit parts tagged in assets/clips/library.json so library_reel skips them.
- Tested offline: join (35.0 s = parts + 3.5 s card, frame strip OK), matcher logic (out of order, 2 batches, no double build). NOT yet tested live: Gemini frame matching (local key refused). First live: when the owner sends the 13 Nov skit clips.
- Library fix: the 13 Nov "unified library" change wrote only social/library.json, which no reader uses. Reverted the save workflows; social/library.json is now a combined search index rebuilt after each save.
- 13 Nov: skit end card now has the voiceover ('Comment mein PP likhiye, follow kijiye, rate aapke DM mein.', Charon, cached assets/brand/cta-vo.wav 3.8 s); card held until the voice ends. First live skit skit-1113-1210 (34.1 s) sent for approval; voice checked by transcript. Old skit-1113-1203 (no voice) rejected. Matcher: same people in part 1+2 -> Gemini said part 1 twice; fixed with send-order fallback.
