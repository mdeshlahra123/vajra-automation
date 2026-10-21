param([ValidateSet("any","reel","image")][string]$Type = "any")
# VAJRA daily poster: Instagram + Facebook together, from social\queue.json.
# -Type reel  = next unposted reel (morning task), -Type image = next unposted post (night task).
# Picks the first post with empty "posted", publishes to both, verifies IG caption,
# marks it posted, logs to social\post-log.txt. Safe to run once a day.
$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
$log  = "$base\post-log.txt"
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

$q = Get-Content "$base\queue.json" -Raw | ConvertFrom-Json
$pending = $q.posts | Where-Object { -not $_.posted }
if ($Type -eq "reel")  { $pending = $pending | Where-Object { $_.video } }
if ($Type -eq "image") { $pending = $pending | Where-Object { -not $_.video } }
$item = $pending | Select-Object -First 1
if (-not $item) { Log "QUEUE EMPTY ($Type) - nothing to post. Add more items to queue.json."; exit 0 }

$cap = [IO.File]::ReadAllText("$base\$($item.caption)", [Text.Encoding]::UTF8).Replace("`r`n","`n").Trim()
Log "POSTING $($item.id)"

# ---- Instagram ----
$igOk=$false; $igId=""
try {
  if ($item.video) {
    # Reel: upload by URL, then wait until Instagram finishes processing
    $c = PostUtf8 "$v/$ig/media" @{ media_type="REELS"; video_url=$item.video; caption=$cap; share_to_feed="true"; access_token=$t }
    $st = ""
    for ($i=0; $i -lt 40 -and $st -ne "FINISHED"; $i++) {
      Start-Sleep 15
      $st = (GetUtf8 "$v/$($c.id)?fields=status_code&access_token=$t").status_code
      if ($st -eq "ERROR") { throw "Reel processing failed" }
    }
    if ($st -ne "FINISHED") { throw "Reel still processing after 10 min" }
  } else {
    $c = PostUtf8 "$v/$ig/media" @{ image_url=$item.image; caption=$cap; access_token=$t }
    Start-Sleep 5
  }
  $p = PostUtf8 "$v/$ig/media_publish" @{ creation_id=$c.id; access_token=$t }
  $igId = $p.id
  $live = GetUtf8 "$v/$igId`?fields=caption,permalink&access_token=$t"
  if ((([string]$live.caption).Replace("`r`n","`n").Trim()) -ceq $cap) { $igOk=$true; Log "  IG OK $($live.permalink)" }
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
  $item.posted = (Get-Date -Format "yyyy-MM-dd")
  ($q | ConvertTo-Json -Depth 6) | Set-Content "$base\queue.json" -Encoding UTF8
  $left = ($q.posts | Where-Object { -not $_.posted }).Count
  Log "  DONE. $left posts left in queue."
  if ($left -le 2) { Log "  LOW QUEUE WARNING: add more posts soon." }
} else { Log "  NOT marked posted (IG failed). Will retry next run." }
