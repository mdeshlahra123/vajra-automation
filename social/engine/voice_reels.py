"""Give silent reels a Charon voiceover + light music, then send each to Telegram for approval (normal approve flow).
Lines are hand-written to match exactly what is on screen (owners: no silent reels, 27 Oct)."""
import json, os, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import gem
from make_reel import A, MUSIC_MODEL, tts, mix, dur

END = "Comment mein PP likhiye, rate aapke DM mein."
SITE = "https://vajraformwork.vercel.app/social/"
# reel id -> (source video, caption file, [(start_seconds, line)], end line start)
R = {
 "x7-hisaab": ("x7-hisaab.mp4", "captions/x7-hisaab.txt",
               [(0.1, "Har kuch slab pe naya ply?"), (2.2, "VAJRA PP ek aadmi utha leta hai."), (4.2, "Ply se do-teen guna zyada chalti hai."),
                (6.6, "Sahi handling ke saath."), (8.1, "Ply baar-baar khareedna band.")], 10.2),
 "x8-column": ("x8-column.mp4", "captions/x8-column.txt",
               [(0.1, "Sariya cage taiyaar."), (2.1, "PP panel lagao."), (4.1, "Seedha aur majboot."), (6.1, "Column ready, saaf finish.")], 8.2),
 "x9-halka": ("x9-halka.mp4", "captions/x9-halka.txt",
              [(0.1, "Shuttering itni bhaari kyun?"), (2.1, "Ek haath se utha lo."), (4.1, "Andar se hollow, isliye halki."), (6.1, "Phir bhi tooti nahi.")], 8.2),
 "samples-40": ("samples-40.mp4", "captions/samples-40.txt", [(0.1, "Aaj chaalis se zyada free samples pack hue."), (3.6, "Ek feet ka VAJRA piece, pack karke courier ke liye ready."), (8.0, "Poore India mein jaa rahe hain."), (10.2, "Aapka bhi chahiye?")], 12.6),
 "qa-rate": ("qa-rate.mp4", "captions/qa-rate.txt", [(0.3, "Aapne poocha, rate kya hai?"), (2.8, "Sheet ka rate mat dekho. Har dhalai ka hisaab dekho.")], 7.9),
 "qa-kahan": ("qa-kahan.mp4", "captions/qa-kahan.txt", [(0.3, "Surat, Noida mein milega?"), (2.8, "Haan. Poore India mein dispatch hota hai.")], 7.9),
 "qa-size": ("qa-size.mp4", "captions/qa-size.txt", [(0.3, "Size kya hai?"), (2.8, "Aath bai chaar feet, baarah mm. Andar se hollow.")], 7.9),
 "qa-toot": ("qa-toot.mp4", "captions/qa-toot.txt", [(0.3, "Toot-foot hota hai kya?"), (2.8, "Chhat se phenk ke dekha. Khud dekh lo.")], 7.9),
 "qa-mehnga": ("qa-mehnga.mp4", "captions/qa-mehnga.txt", [(0.3, "Mehnga nahi hai?"), (2.8, "Ply se do-teen guna zyada chalti hai, sahi handling ke saath.")], 7.9),
}
work = A("work", "voice"); os.makedirs(work, exist_ok=True); os.makedirs(A("social", "media"), exist_ok=True)
music = os.path.join(work, "music.mp3")
r = gem.interact(MUSIC_MODEL, "20 second calm modern Indian instrumental background track for a short construction product reel, "
                 "soft percussion and light guitar, positive, low energy so a voiceover sits on top, no vocals, no lyrics", response_format={"type": "audio"})
gem.save_first(r, "audio", music)
pend_path = A("social", "pending.json"); pend = json.load(open(pend_path, encoding="utf-8"))
ids = []
for name, (src, cap, lines, end_at) in R.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    v = os.path.join(work, src); urllib.request.urlretrieve(SITE + src, v)
    total = dur(v); vos, starts = [], []
    t = 0.0
    for i, (st, line) in enumerate(lines + [(end_at, END)]):
        f = os.path.join(work, f"{name}-{i}.wav"); d = tts(line, f)
        st = max(st, t + 0.15)          # never let two lines overlap
        vos.append(f); starts.append(round(st, 2)); t = st + d
    if t > total - 0.2:
        print("WARN voice longer than video", name, round(t, 1), round(total, 1))
    rid = f"{name}-v"; out = A("social", "media", rid + ".mp4")
    mix(v, vos, starts, total, music, out)
    pend["items"].append({"id": "reel-" + rid, "title": f"Awaaz wali: {name}", "file": f"social/media/{rid}.mp4", "caption": cap,
                          "position": "end", "status": "draft", "cover": SITE + src.replace(".mp4", "-cover.jpg")})
    ids.append("reel-" + rid); print("made", rid, round(total, 1), "s")
json.dump(pend, open(pend_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for i in ids:
    subprocess.run([sys.executable, A("social", "tg.py"), "send", i], check=False)
