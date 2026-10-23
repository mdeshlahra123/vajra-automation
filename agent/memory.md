# VAJRA brain memory

## Known so far (from setup, 24 Oct 2026)
- Best organic reel ever: 21 Oct "Har 5 slab pe naya ply? Saal ka kharcha..." — ~103k reach, 900 saves, 1.2k shares. Money/cost comparison (ply vs VAJRA per year) works best.
- Image posts get ~100-170 reach; reels get thousands. Prefer reels.
- Real site footage from Shobhit (column shuttering) is valued; real reels alternate with others in the queue.
- Ads (lead form, Raipur/Durg +40 km): "Kharcha - Har 5 slab pe naya ply" ~₹10/lead is best; Reel B paused 24 Oct (CPL rising ~₹27). Budget ₹100/day, prepaid balance low (~₹248 on 24 Oct) — owners decide top-ups.
- Owners: Mehul (shows as "MrBeast" on Telegram), Shobhit (does site work, sends clips).

## Test run (24 Oct 2026)
- Setup test run executed. Queue status: 17 pending reels, 9 pending images, 0 waiting approval. Last posted: reel-x2-throw & v-n2-oneman (23 Oct).
- Best reel confirmed: "Har 5 slab pe naya ply? Saal ka kharcha..." (reel-a1-kharcha, 21 Oct) with ~103k reach, 900 saves, 1.2k shares.
- Diagnostics: GitHub Actions composite action `run-gemini-cli@v0` does not inherit job-level `env:`, causing `META_ADS_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `GH_TOKEN` to be unset in the agent runtime. Recommendation for Mehul: In `.github/workflows/agent.yml`, export secrets to `$GITHUB_ENV` in a step before `Brain`.
