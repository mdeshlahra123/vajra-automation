# VAJRA brain memory

## Known so far (from setup, 24 Oct 2026)
- Best organic reel ever: 21 Oct "Har 5 slab pe naya ply? Saal ka kharcha..." — ~103k reach, 900 saves, 1.2k shares. Money/cost comparison (ply vs VAJRA per year) works best.
- Image posts get ~100-170 reach; reels get thousands. Prefer reels.
- Real site footage from Shobhit (column shuttering) is valued; real reels alternate with others in the queue.
- Ads (lead form, Raipur/Durg +40 km): "Kharcha - Har 5 slab pe naya ply" ~₹10/lead is best; Reel B paused 24 Oct (CPL rising ~₹27). Budget ₹100/day, prepaid balance low (~₹248 on 24 Oct) — owners decide top-ups.
- Owners: Mehul (shows as "MrBeast" on Telegram), Shobhit (does site work, sends clips).

## Test run 1 (24 Oct 2026)
- Setup test run executed. Queue status: 17 pending reels, 9 pending images, 0 waiting approval.

## Test run 2 (24 Oct 2026)
- Status checked: 17 pending reels, 9 pending images in queue, 0 waiting approval. Last posted: reel-x2-throw & v-n2-oneman (23 Oct).
- Best recent reel: reel-a1-kharcha ("Har 5 slab pe naya ply? Saal ka kharcha...", 21 Oct, ~103k reach, 900 saves, 1.2k shares).
- Ads and queue untouched as instructed (no reels started, no ads paused/resumed).
- Telegram message attempted. Failed due to missing `TELEGRAM_BOT_TOKEN` in runtime environment.
- Fix for Mehul: GitHub Actions does not expand `${{ secrets.* }}` inside `jobs.<job>.env`. In `.github/workflows/agent.yml`, move the `env:` block with `${{ secrets.* }}` directly onto the step `Pass secrets to the brain's tools` so the tokens are populated in `$GITHUB_ENV`.

## Test run 3 (24 Oct 2026)
- Status checked: 719 followers, 17 pending reels, 9 pending images in queue.
- Best recent reel: reel-a1-kharcha ("Har 5 slab pe naya ply? Saal ka 2.6 lakh", 21 Oct, 107.4k reach, 979 saves, 1,295 shares).
- Telegram test successful: connection confirmation message delivered via Telegram API.
- No reels started, no ads changed as instructed.


## 24 Oct (research + ads)
- Promoted organic reels to ads (same ad set, same budget): L5 Throw (ad 120251540931460600), L6 Khokla 'Har 5 dhalai' (ad 120251540931990600). Active now: Kharcha, G5, L5, L6. Judge L5/L6 after ~Oct 28 (Rs150 spend each).

## 24 Oct: WhatsApp test (owner chose)
- Lead form ad set 120251450839500600 PAUSED. New WhatsApp ad set 120251541042080600 (Rs100/day, same targeting) with ad L7 WhatsApp - Kharcha. Results = WhatsApp chats started. Compare cost per chat vs ~Rs16/lead after ~3-4 days (~Rs300 spend), then report to owners; don't resume lead form without telling them. Balance Rs747 on 24 Oct.

## 24 Oct (daily run)
- Reel `reel-x2-throw` (23 Oct) confirmed strong toughness appeal: 6.8k reach, 7.5k views, 37 comments, 30 saves+shares in first 24h.
- Reel `reel-h1-hisaab` (22 Oct) also performed well: 5.7k reach, 123 comments, 66 saves+shares.
- Queue healthy with 17 pending reels (no new AI reel needed, > 6). Next up: `reel-h2-ekhaath`.
- WhatsApp test (L7 Kharcha) running, ₹747 balance. Monitoring chat costs over next 3 days.

## 2026-10-24 USE-COUNT RULE (owners)
- Never say a number of uses (40/40+/40-50 etc.), no '5 slab' ply hook, no Rs 88 / Rs 416 per dhalai, no 2.6 vs 1.1 lakh. Only: 'Sahi handling ke saath ply se 2-3 guna zyada chalti hai.' Shobhit: ply actually lasts 8-10 uses. Older entries above that quote those numbers are history, not copy to reuse.
- TODO after WhatsApp test (~27-28 Oct): L7 ad text still says '40+ baar / 1.1 lakh' -> owners/Kiro will replace with a new creative using the 2-3 guna line. Don't promote old reels whose video shows 40+/lakh numbers (a1-kharcha, m1-story).
