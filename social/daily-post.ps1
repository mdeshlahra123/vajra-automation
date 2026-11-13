param([ValidateSet("any","reel","image","trial")][string]$Type = "any", [string]$Id = "", [switch]$DryRun)
# VAJRA daily poster: Instagram + Facebook together, from social\queue.json.
# -Type reel  = next unposted reel (morning task), -Type image = next unposted post (night task).
# -Id xyz    = force-post specific item by id, ignoring queue order.
# Picks the first post with empty "posted", publishes to both, verifies IG caption,
# marks it posted, logs to social\post-log.txt. Safe to run once a day.
$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
$log  = "$base/post-log.txt"
function Log($m){ $line = (Get-Date -Format "yyyy-MM-dd HH:mm") + "  " + $m; Add-Content $log $line; Write-Output $line }

$t = $env:META_TOKEN
if (-not $t) { $raw = Get-Content "$env:USERPROFILE\.kiro\settings\mcp.json" -Raw; $t = [regex]::Match($raw, '"(EAA[A-Za-z0-9]+)"').Groups[1].Value }
$v = "https://graph.facebook.com/v24.0"
$ig = "17841424780649708"
$pageId = "1296793536861294"
$pageTok = (Invoke-RestMethod "$v/$pageId`?fields=access_token&access_token=$t").access_token

function E($e){ $r=$e.Exception.Response; if($r){ (New-Object IO.StreamReader($r.GetResponseStream())).ReadToEnd() } else { $e.Exception.Message } }
function PostUtf8($url,$fields){ $pairs=foreach($k in $fields.Keys){[uri]::EscapeDataString($k)+"="+[uri]::EscapeDataString([string]$fields[$k])}; $b=[Text.Encoding]::UTF8.GetBytes(($pairs -join "&")); $wc=New-Object Net.WebClient; $wc.Headers["Content-Type"]="application/x-www-form-urlencoded; charset=utf-8"; [Text.Encoding]::UTF8.GetString($wc.UploadData($url,"POST",$b))|ConvertFrom-Json }
function GetUtf8($url){ $wc=New-Object Net.WebClient; $wc.Encoding=[Text.Encoding]::UTF8; $wc.DownloadString($url)|ConvertFrom-Json }

$q = Get-Content "$base/queue.json" -Raw | ConvertFrom-Json
$pending = $q.posts | Where-Object { -not $_.posted }
# Force-post specific item if -Id is given
if ($Id) {
  $item = $q.posts | Where-Object { $_.id -eq $Id } | Select-Object -First 1
  if (-not $item) { Log "ERROR: Item $Id not found in queue.json"; exit 1 }
  if ($item.posted) { Log "ERROR: Item $Id already posted on $($item.posted)"; exit 1 }
  Log "FORCE-POST: $Id (ignoring queue order)"
} else {
  # Evening slot (owner, 30 Oct): Mon-Sat IST the 19:30 run posts the next reel tagged "evening": true; Sunday a photo/carousel.
  # Morning never takes evening-tagged reels. If no evening reel is left, the evening run falls back to a photo.
  $istDay = [string][DateTime]::UtcNow.AddHours(5.5).DayOfWeek
  # 1 Nov (owner): ONE main reel a day at 19:30, every day incl. Sunday; evening photo only if no reel at all. Morning = Trial Reel (non-followers first).
  $evDay = ($Type -eq "image")
  if ($Type -eq "reel" -and @($q.trials | Where-Object { -not $_.posted -and $_.video }).Count) { $morning = $true; $Type = "trial" }   # morning: trial pool first, else a queue reel posted as trial
  if ($Type -eq "trial") { $pending = @($q.trials | Where-Object { -not $_.posted -and $_.video }) }   # extra daily Trial Reel from the trial pool (owner 31 Oct)
  $all = $pending
  if ($Type -eq "reel")  { $pending = $pending | Where-Object { $_.video -and -not $_.evening } }
  if ($Type -eq "image") { $pending = $pending | Where-Object { -not $_.video } }
  $item = $pending | Select-Object -First 1
  # only items whose media is really live on the website (an approved reel can still be waiting for upload)
  function Live($x) {   # waits up to ~4 min: the website (Vercel) may still be deploying a file pushed a moment ago
    if (-not (Test-Path "$base/$($x.caption)")) { Log "  SKIP (caption file missing): $($x.id) -> $($x.caption)"; return $false }  # 2 Nov: a missing caption used to crash the whole run (line 66)
    $u = if ($x.video) { $x.video } else { $x.image }
    for ($k = 0; $k -lt 16; $k++) { try { if ((Invoke-WebRequest $u -Method Head -UseBasicParsing -TimeoutSec 30).StatusCode -eq 200) { return $true } } catch {}; Start-Sleep 15 }
    Log "  SKIP (file not live after 4 min): $($x.id)"; $false }
  $item = $pending | Where-Object { Live $_ } | Select-Object -First 1
  if (-not $item -and $Type -eq "reel") { $item = $all | Where-Object { $_.video } | Where-Object { Live $_ } | Select-Object -First 1 }  # never skip a morning: use an evening-tagged reel if needed
  if ($evDay) { $ev = $all | Where-Object { $_.video -and $_.evening } | Where-Object { Live $_ } | Select-Object -First 1; if ($ev) { $item = $ev } elseif (-not ($item -and $item.video)) { $any = $all | Where-Object { $_.video } | Where-Object { Live $_ } | Select-Object -First 1; if ($any) { $item = $any } } }
}
# Scheduled stand-alone Stories (queue.json "stories": [{id, image|video, date, posted}]) go out with the morning run
if (($Type -eq "reel" -or $morning) -and -not $DryRun -and $q.stories) {
  $todayS = [DateTime]::UtcNow.AddHours(5.5).ToString("yyyy-MM-dd")
  foreach ($s in @($q.stories | Where-Object { -not $_.posted -and $_.date -le $todayS })) {
    try {
      $sp = if ($s.video) { @{ media_type="STORIES"; video_url=$s.video; access_token=$t } } else { @{ media_type="STORIES"; image_url=$s.image; access_token=$t } }
      $sc = PostUtf8 "$v/$ig/media" $sp
      for ($i=0; $i -lt 20; $i++) { Start-Sleep 10; $ss=(GetUtf8 "$v/$($sc.id)?fields=status_code&access_token=$t").status_code; if ($ss -eq "FINISHED" -or $ss -eq "ERROR") { break } }
      $null = PostUtf8 "$v/$ig/media_publish" @{ creation_id=$sc.id; access_token=$t }
      $s.posted = $todayS; Log "  STORY (scheduled) OK $($s.id)"
    } catch { Log ("  STORY (scheduled) ERR $($s.id) " + (E $_)) }
  }
  ($q | ConvertTo-Json -Depth 6) | Set-Content "$base/queue.json" -Encoding UTF8
}
# Guard: max one reel and one image per IST day (GitHub cron can run late or after a manual post)
# Skip guards when force-posting with -Id
if (-not $Id) {
  if ($Type -eq "trial" -and -not $DryRun -and $item) { $td = [DateTime]::UtcNow.AddHours(5.5).ToString("yyyy-MM-dd"); if (@($q.trials | Where-Object { [string]$_.posted -eq $td }).Count) { Log "SKIP: trial already posted today"; exit 0 } }
  if ($Type -ne "any" -and $Type -ne "trial" -and -not $DryRun -and $item) {
    $today = [DateTime]::UtcNow.AddHours(5.5).ToString("yyyy-MM-dd")
    $done = $q.posts | Where-Object { $_.posted -and ([string]$_.posted -eq $today) -and $(if ($Type -eq "reel") { $_.video -and $_.slot -ne "evening" } else { (-not $_.video) -or $_.slot -eq "evening" }) }
    if ($done) { Log "SKIP: $Type already posted today ($today IST): $($done[0].id)"; exit 0 }
  }
}
if (-not $item) { Log "QUEUE EMPTY ($Type) - nothing to post. Add more items to queue.json."; exit 0 }

$cap = [IO.File]::ReadAllText("$base/$($item.caption)", [Text.Encoding]::UTF8).Replace("`r`n","`n").Trim()
Log "POSTING $($item.id)"

# ---- Instagram ----
$igOk=$false; $igId=""
try {
  if ($item.video) {
    # Reel: upload by URL, then wait until Instagram finishes processing
    $prm = @{ media_type="REELS"; video_url=$item.video; caption=$cap; share_to_feed="true"; access_token=$t }
    if ($item.cover) { $prm.cover_url = $item.cover }   # brand-style grid cover (social/engine/cover.py)
    if ($item.ai) { $prm.is_ai_generated = "true" }   # Instagram "AI info" label for AI-made reels
    $prm.audio_name = "VAJRA PP Shuttering"            # name our original audio (shows on the reel's audio page)
    # Trial Reel (shown to non-followers first; Instagram shares it to followers itself if it performs).
    # Morning reels on Tue/Thu/Sat, or any item with "trial": true. "trial": false forces a normal reel.
    $trialDay = ($Type -eq "reel")   # 1 Nov: every morning reel is a Trial Reel
    if (($Type -eq "trial") -or ($item.trial -eq $true) -or ($trialDay -and $item.trial -ne $false)) { $prm.trial_params = '{"graduation_strategy":"SS_PERFORMANCE"}' }
    try { $c = PostUtf8 "$v/$ig/media" $prm }
    catch {   # if Instagram refuses trial/audio name, post as a normal reel instead of missing the day
      Log ("  reel extras refused, posting plain: " + (E $_)); $prm.Remove("trial_params"); $prm.Remove("audio_name"); $c = PostUtf8 "$v/$ig/media" $prm }
    if ($prm.trial_params) { Log "  TRIAL reel (non-followers first, auto-share if it performs)" }
    $st = ""
    for ($i=0; $i -lt 40 -and $st -ne "FINISHED"; $i++) {
      Start-Sleep 15
      $st = (GetUtf8 "$v/$($c.id)?fields=status_code&access_token=$t").status_code
      if ($st -eq "ERROR" -and ($prm.trial_params -or $prm.audio_name)) {   # retry once as a plain reel
        Log "  processing error with trial/audio name, retrying plain"; $prm.Remove("trial_params"); $prm.Remove("audio_name")
        $c = PostUtf8 "$v/$ig/media" $prm; $st = ""; continue }
      if ($st -eq "ERROR") { throw "Reel processing failed" }
    }
    if ($st -ne "FINISHED") { throw "Reel still processing after 10 min" }
  } elseif ($item.slides) {
    # Carousel: one container per slide, then the carousel container
    $kids = foreach ($s in $item.slides) { (PostUtf8 "$v/$ig/media" @{ image_url=$s; is_carousel_item="true"; access_token=$t }).id }
    Start-Sleep 5
    $c = PostUtf8 "$v/$ig/media" @{ media_type="CAROUSEL"; children=($kids -join ","); caption=$cap; access_token=$t }
    for ($i=0; $i -lt 20; $i++) { Start-Sleep 6; if ((GetUtf8 "$v/$($c.id)?fields=status_code&access_token=$t").status_code -eq "FINISHED") { break } }
  } elseif ($item.reel) {
    # Photo reel (reels reach far more people), with the designed photo as the grid cover so the profile looks the same
    $c = PostUtf8 "$v/$ig/media" @{ media_type="REELS"; video_url=$item.reel; cover_url=$item.image; caption=$cap; share_to_feed="true"; access_token=$t }
    $st = ""
    for ($i=0; $i -lt 40 -and $st -ne "FINISHED"; $i++) {
      Start-Sleep 15
      $st = (GetUtf8 "$v/$($c.id)?fields=status_code&access_token=$t").status_code
      if ($st -eq "ERROR") { throw "Photo reel processing failed" }
    }
    if ($st -ne "FINISHED") { throw "Photo reel still processing after 10 min" }
  } else {
    $c = PostUtf8 "$v/$ig/media" @{ image_url=$item.image; caption=$cap; access_token=$t }
    Start-Sleep 5
  }
  if ($DryRun) { Log "  DRYRUN: IG upload OK (container $($c.id)), not published. Next: $($item.id)"; exit 0 }
  $p = PostUtf8 "$v/$ig/media_publish" @{ creation_id=$c.id; access_token=$t }
  $igId = $p.id
  $live = GetUtf8 "$v/$igId`?fields=caption,permalink&access_token=$t"
  $noTag = { param($x) (([string]$x).Replace("`r`n","`n") -replace "(?<!\S)#\w+","" -replace "\s+"," ").Trim() }
  if ((& $noTag $live.caption) -ceq (& $noTag $cap)) {
    $igOk=$true; Log "  IG OK $($live.permalink)"
    # Auto-reshare of the post to Story is OFF (owner, 26 Oct: same content twice, no point).
    # Stand-alone Stories still go out from queue.json "stories".
    if ($false) { try {
      $sp = if ($item.video) { @{ media_type="STORIES"; video_url=$item.video; access_token=$t } }
            else { @{ media_type="STORIES"; image_url=$(if ($item.slides) { $item.slides[0] } else { $item.image }); access_token=$t } }
      $sc = PostUtf8 "$v/$ig/media" $sp
      for ($i=0; $i -lt 20; $i++) { Start-Sleep 10; $ss=(GetUtf8 "$v/$($sc.id)?fields=status_code&access_token=$t").status_code; if ($ss -eq "FINISHED" -or $ss -eq "ERROR") { break } }
      $sx = PostUtf8 "$v/$ig/media_publish" @{ creation_id=$sc.id; access_token=$t }; Log "  STORY OK $($sx.id)"
    } catch { Log ("  STORY ERR " + (E $_)) } }
  }
  else { Invoke-RestMethod -Method Delete "$v/$igId`?access_token=$t" | Out-Null; Log "  IG CAPTION MISMATCH - deleted, skipped" }
} catch { Log ("  IG ERR " + (E $_)) }

# ---- Facebook Page (photo + caption) ----
try {
  if ($item.video) {
    $f = PostUtf8 "$v/$pageId/videos" @{ file_url=$item.video; description=$cap; access_token=$pageTok }
    Log "  FB OK video $($f.id)"
  } else {
    $f = PostUtf8 "$v/$pageId/photos" @{ url=$item.image; caption=$cap; access_token=$pageTok }
    Log "  FB OK post $($f.post_id)"
  }
} catch { Log ("  FB ERR " + (E $_)) }

# ---- mark posted (only if IG succeeded; FB-only failure still marks, IG is primary) ----
if ($igOk) {
  $item.posted = [DateTime]::UtcNow.AddHours(5.5).ToString("yyyy-MM-dd")
if ($Type -eq "image") { $item | Add-Member -NotePropertyName slot -NotePropertyValue "evening" -Force }
  ($q | ConvertTo-Json -Depth 6) | Set-Content "$base/queue.json" -Encoding UTF8
  $left = ($q.posts | Where-Object { -not $_.posted }).Count
  Log "  DONE. $left posts left in queue."
  if ($left -le 2) { Log "  LOW QUEUE WARNING: add more posts soon." }
} else { Log "  NOT marked posted (IG failed). Will retry next run." }
