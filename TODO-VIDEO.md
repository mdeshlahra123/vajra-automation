# VAJRA video work: open asks and progress

Read this first in every session. Update it after every change. Owner rules: act without asking, report afterwards,
no money spent, review the real output (frames + timing) before saying "done".

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
| 3 | Animated text reels | DONE 12 Nov. social/engine/text_reel.py + text-reel.yml (Sat 10:00 IST GitHub schedule). Formats: galtiyan (title, 4 items slide in, red X each, green fix line) and myth (MYTH, strike-through, FACT). No voice; music bed assets/music/text-bed-1.mp3 (made once). Frame-audited locally (text fits, no orphans). GitHub run OK. Myth facts = approved claims only (an AI-written fact broke the rules and was removed from the queue). Next: before/after format. |
| 4 | Reviewer step | PARTLY 12 Nov: polish.py checks every caption sits inside its voice line, none on the end card, no overlaps; any failure = CHECK -> reel goes for approval, not auto-queue. Still to add: frame audit image sent with each new reel's FYI. |
| 5 | Long-video picture sync | DONE 12 Nov (code), first live use Thu 20 Nov. assign_sentences(): one library item per sentence by meaning (free Gemini text), max 3 uses per item, shots at least 3 s, cuts on sentence starts. Fallback = rotation per chapter (offline-tested). If the first live build looks off, tune the prompt in assign_sentences. |
| 6 | IG long-video | DONE 12 Nov. Tested: Meta accepts a 6 min reel from video_url (error 2207076 is transient, retried up to 4x). Resumable upload is broken at Meta (ProcessingFailedError). long_video.ig_long hosts the file as a TEMPORARY GitHub release asset, creates the container, publishes, deletes the release. First live use Thu 20 Nov. (A 52 MB test file remains in git history under social/tmp.) |

## Known facts / traps
- Gemini free credits nearly gone (about Rs 345 on 11 Nov). AI video generation disabled in make_reel.py. Owner must set the spend cap to Rs 1,600 in AI Studio.
- Hindi whisper splits Hinglish words differently; never map script words to heard words by position over a whole reel.
- GitHub apt installs can hang: always wrap in `timeout 240`.
- mediapipe on GitHub needs libgl1 libegl1 libgles2; faster-whisper audio is loaded via an ffmpeg pipe (load_wav) to avoid PyAV clashes.
- Test helpers: .github/workflows/polish-test.yml (input id), long-video.yml (mode=build publish=false).
