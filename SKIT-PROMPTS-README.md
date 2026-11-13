# DAILY SKIT/DIALOGUE PROMPTS - Complete

**Created: 13 Nov 2026, 12:00 PM**

## What This Is:

**NEW content type**: Character conversations/skits (NO voiceover needed).

Instead of problem-voiceover-reveal format, now you get:
- **Contractor-Labour-Engineer TALKING** to each other
- Real dialogue in Hinglish (like site conversations)
- 3-part stories (setup → discussion → PP reveal)

## The Format:

Each day = **3 prompts** that tell ONE story:

**Part 1** (10 sec): Problem setup
- Contractor stressed about ply cost, OR
- Labour struggling with heavy ply, OR
- Ply breaking/damaged

**Part 2** (10 sec): Reaction/discussion  
- Characters talking about the problem
- Worried faces, explaining issues

**Part 3** (10 sec): PP solution
- Showing grey PP sheets
- Happy/relieved, mentioning benefits
- Natural ending

**Total**: ~30 seconds (extend each part to 10 sec in Flow)

**End card**: "VAJRA PP Shuttering | Follow kijiye, comment mein likhiye PP"

## Daily Scenarios (15+ angles, rotate, never repeat within 30 days):

1. **Contractor ka budget tension** - ply cost eating profit every month
2. **Labour ke liye halka hai** - two men for ply vs one man for PP
3. **Ply tooti, contractor gussa** - board breaks, client angry
4. **Barish mein ply kharab** - monsoon damage, swollen boards
5. **Engineer ko smooth finish chahiye** - rough ply finish vs smooth PP
6. **Labour ki site gossip** - tea break, talking about neighbour using PP
7. **Mistri ka naya idea** - cutting/sizing problems
8. **Client visit surprise** - impressed by smooth column
9. **De-shuttering tension** - ply cracks vs PP slides off easy
10. **Junior engineer training** - senior explaining modern technique
11. **Site pe naya labour** - first day, learns PP is lighter
12. **Cost comparison meeting** - contractors discussing materials
13. **Column finish check** - inspector comparing surfaces
14. **Site meeting material review** - group discussing shuttering options
15. **Surprise inspection** - government officer impressed

## How It Runs:

**Daily prompts** (09:30 IST):
- GitHub Actions sends 3-part skit prompts to Telegram
- You make the 3 videos in Flow (extend each to ~10 sec)

**After you make videos**:
- Send all 3 videos to Telegram
- Reply with: `make skit: Labour ke liye halka` (or whatever the title is)
- Apps Script triggers `make-skit.yml` workflow
- **I automatically**:
  - Download 3 videos
  - Join them in sequence
  - Add brand end card (cta-card.mp4, 3.5 sec)
  - Generate Instagram caption
  - Send finished reel to Telegram for approval
  
**Total reel**: ~33.5 seconds (30 sec dialogue + 3.5 sec end card)

## Example Output (Telegram message):

```
🎬🗣️ SKIT PROMPT – Labour ke liye halka hai

3 parts (extend each to 10 sec in Flow, total ~30 sec). Paste karo ek-ek karke:

Part 1/3:
Two Indian labourers struggling to carry one heavy brown plywood board across a site, straining, slow walk. Dialogue: 'Bhai sambhal ke, bhaari hai ye toh... dono ko pakad'

Part 2/3:
They set it down, tired, wiping sweat. One labourer says: 'Har baar isi chakkar mein peeth dard... do-do aadmi chahiye'

Part 3/3:
One labourer alone easily carrying a grey PP sheet on his shoulder, walking fast, smiling. Dialogue: 'Arre bhai, ye toh akele uthati hai! Itni halki plastic... koi problem nahi'
```

## Why Skits Work (Competitor Research):

Based on TikTok/Instagram construction comedy trends:
- ✅ **Relatable site moments** (everyone knows contractor-labour conversations)
- ✅ **Natural Hinglish dialogue** (how real workers talk)
- ✅ **Before/after reactions** (problem → relief emotional arc)
- ✅ **Character-driven** (people remember personalities, not products)
- ✅ **Shareable** (funny/relatable moments get shared more than voiceover reels)

Top construction content creators use:
- Worker wisdom skits (labour giving smart advice)
- Contractor confusion moments (measurement errors, wrong orders)
- Site gossip/tea break conversations
- Client visit reactions

## What's Different from Current Reels:

| Current (Voiceover) | New (Skit) |
|---------------------|------------|
| Problem voiceover + b-roll | Characters TALKING about problem |
| One narrator voice | Multiple people conversing |
| Serious tone | Natural, sometimes funny |
| 15-20 sec | 30 sec (3x10) |
| Same format every day | Different characters/situations |

## Integration with Existing System:

**Flow brief stays the same** (b-roll clips, 08:00 IST)
- Problem shots (ply damage, worker tired, etc.)
- Construction scenes
- VAJRA reveal shots

**Skit prompts NEW** (dialogue scenarios, 09:30 IST)
- Full character conversations
- 3-part stories
- Natural endings

**Both go to Telegram** → Owner picks what to make

## Files:

- ✅ `social/engine/skit_prompts.py` - generator (15 scenarios + AI generation)
- ✅ `.github/workflows/skit-prompts.yml` - daily automation (09:30 IST)
- ✅ `social/skit-prompts-state.json` - tracks used angles (prevents repeats)

## Next Steps (Once Working):

1. Owner makes 2-3 skits, posts them
2. Check which performs better: voiceover vs skit format
3. Adjust daily mix based on what works:
   - If skits win: more skit prompts
   - If both work: alternate days
   - If voiceover wins: keep as bonus option

## Status:

✅ **DONE**: Skit prompt system built
✅ **TESTED**: Fallback scenarios work (Gemini API failed, bank worked)
✅ **AUTOMATED**: Daily workflow created (09:30 IST)
⏳ **PENDING**: First live test (tomorrow 14 Nov 09:30)

---

**Owner request**: "i need daily new unique angle prompts, split to 3 parts as gemini makes 10 sec video, so i will extend. skit content like people talking, no voiceover needed"

**Status**: ✅ DONE
