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

