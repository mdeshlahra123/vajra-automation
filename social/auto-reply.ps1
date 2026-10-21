param([switch]$DryRun)
# VAJRA auto-reply: replies once to every new comment on our Instagram + Facebook posts,
# including the hidden ad copies. Remembers what it replied to in social\replied.json.
# Run:  powershell -NoProfile -ExecutionPolicy Bypass -File social\auto-reply.ps1 [-DryRun]
$ErrorActionPreference = "Stop"
$base   = $PSScriptRoot
$log    = "$base/reply-log.txt"
$state  = "$base/replied.json"
$maxPerRun = 30
$maxAgeDays = 7

function Log($m){ $line = (Get-Date -Format "yyyy-MM-dd HH:mm") + "  " + $m; Add-Content $log $line -Encoding UTF8; Write-Output $line }
function E($e){ if ($e.ErrorDetails -and $e.ErrorDetails.Message) { $e.ErrorDetails.Message } else { $e.Exception.Message } }
function GetJ($url){ $wc = New-Object Net.WebClient; $wc.Encoding = [Text.Encoding]::UTF8; $wc.DownloadString($url) | ConvertFrom-Json }
function PostUtf8($url,$fields){ $pairs=foreach($k in $fields.Keys){[uri]::EscapeDataString($k)+"="+[uri]::EscapeDataString([string]$fields[$k])}; $b=[Text.Encoding]::UTF8.GetBytes(($pairs -join "&")); $wc=New-Object Net.WebClient; $wc.Headers["Content-Type"]="application/x-www-form-urlencoded; charset=utf-8"; [Text.Encoding]::UTF8.GetString($wc.UploadData($url,"POST",$b)) | ConvertFrom-Json }

$t = $env:META_TOKEN
if (-not $t) { $raw = Get-Content "$env:USERPROFILE\.kiro\settings\mcp.json" -Raw; $t = [regex]::Match($raw, '"(EAA[A-Za-z0-9]+)"').Groups[1].Value }
$v = "https://graph.facebook.com/v24.0"
$ig = "17841424780649708"; $igUser = "vajraformwork"
$pageId = "1296793536861294"; $act = "act_1417609487254050"
$pt = (GetJ "$v/$pageId`?fields=access_token&access_token=$t").access_token

# ---- reply texts (rotated so replies don't look like spam) ----
$general = @(
  "Namaste ji 🙏 Rate ₹3,500 + GST per sheet (8x4 ft, 12 mm). Apna slab size (sq ft) aur city bata dijiye, poora hisaab bhej denge. 📞 WhatsApp 83050 70160",
  "Dhanyavaad ji 🙏 PP shuttering sheet ₹3,500 + GST (8x4 ft, 12 mm). Slab kitne sq ft ka hai aur kaunsa sheher? Hisaab bana ke bhejte hain. 📞 83050 70160 (Call/WhatsApp)",
  "Ji zaroor 🙏 Details aur rate ke liye 83050 70160 pe WhatsApp karein, ya slab size + city yahin likh dijiye. ₹3,500 + GST, 8x4 ft, 12 mm."
)
$price = @(
  "Sahi baat ji, sheet ply se mehngi hai 🙏 Par ply 4-5 slab mein khatam, yeh baar-baar chalta hai, isliye har slab ka kharcha kam padta hai. Slab size bataiye, hisaab bhej denge. 📞 83050 70160",
  "Ji, ek baar ka kharcha zyada lagta hai 🙏 Asli fark har slab ke kharche mein hai, ply baar-baar khareedna nahi padta. Apne slab ka hisaab chahiye to 83050 70160 pe WhatsApp karein."
)
$priceWords = 'mahg|mehng|mahang|mehang|costly|expensive|jyada|zyada|bahut|kam karo|discount|sasta'

# ---- what we already replied to ----
$done = @{}
if (Test-Path $state) { (Get-Content $state -Raw | ConvertFrom-Json) | ForEach-Object { $done[$_] = $true } }
$cutoff = (Get-Date).ToUniversalTime().AddDays(-$maxAgeDays)
$replied = 0; $gi = 0; $pi = 0

function PickReply($text){
  if (IsLead $text) {
    $num = [regex]::Match($text, '(?<!\d)[6-9]\d{9}(?!\d)').Value
    if (-not $DryRun) { Add-Content $leadsFile ((Get-Date -Format "yyyy-MM-dd HH:mm") + "  " + $num + "  (comment: " + $text + ")") -Encoding UTF8 }
    return $leadReply
  }
  if ($text -match $priceWords) { $script:pi++; return $price[$script:pi % $price.Count] }
  $script:gi++; return $general[$script:gi % $general.Count]
}
function ShouldSkip($text){
  if ([string]::IsNullOrWhiteSpace($text)) { return $true }
  # junk like ". . . M" : fewer than 2 letters in any script
  return (($text -notmatch '\p{L}{2,}') -and -not (IsLead $text))
}
function IsLead($text){ return ($text -match '(?<!\d)[6-9]\d{9}(?!\d)') }
$leadReply = "Dhanyavaad ji 🙏 Number mil gaya, hamari team jaldi call karegi. 📞 83050 70160"
$leadsFile = "$base/comment-leads.txt"

# ---- collect Instagram media: recent organic posts + ad copies ----
$igMedia = @{}
(GetJ "$v/$ig/media?fields=id,timestamp&limit=15&access_token=$t").data | ForEach-Object { $igMedia[$_.id] = "organic" }
$fbPosts = @{}
$ads = (GetJ "$v/$act/ads?fields=effective_status,creative{effective_instagram_media_id,effective_object_story_id}&limit=50&access_token=$t").data
foreach ($a in $ads) {
  if ($a.effective_status -notin @("ACTIVE","IN_PROCESS","PENDING_REVIEW","PAUSED","CAMPAIGN_PAUSED","ADSET_PAUSED")) { continue }
  if ($a.creative.effective_instagram_media_id) { $igMedia[$a.creative.effective_instagram_media_id] = "ad" }
  if ($a.creative.effective_object_story_id) { $fbPosts[$a.creative.effective_object_story_id] = "ad" }
}
# recent organic Facebook posts and reels
try { (GetJ "$v/$pageId/posts?fields=id,created_time&limit=15&access_token=$pt").data | ForEach-Object { $fbPosts[$_.id] = "organic" } } catch { Log ("FB posts list ERR " + (E $_)) }

# ---- Instagram comments ----
foreach ($mid in $igMedia.Keys) {
  try { $cs = (GetJ "$v/$mid/comments?fields=id,text,username,timestamp,replies{username}&limit=50&access_token=$t").data } catch { Log ("IG read ERR $mid " + (E $_)); continue }
  foreach ($c in $cs) {
    if ($replied -ge $maxPerRun) { break }
    if ($done[$c.id]) { continue }
    if ($c.username -eq $igUser) { $done[$c.id] = $true; continue }
    if ([datetime]$c.timestamp -lt $cutoff) { continue }
    if ($c.replies -and ($c.replies.data | Where-Object { $_.username -eq $igUser })) { $done[$c.id] = $true; continue }
    if (ShouldSkip $c.text) { continue }
    $msg = PickReply $c.text
    if ($DryRun) { Log ("DRY IG [$($igMedia[$mid])] @$($c.username): $($c.text)  ->  $msg"); $replied++; continue }
    try { PostUtf8 "$v/$($c.id)/replies" @{ message = $msg; access_token = $t } | Out-Null; $done[$c.id] = $true; $replied++; Log ("IG [$($igMedia[$mid])] @$($c.username): $($c.text)") ; Start-Sleep 4 }
    catch { Log ("IG reply ERR @$($c.username) " + (E $_)) }
  }
}

# ---- Facebook comments ----
foreach ($postId in $fbPosts.Keys) {
  try { $cs = (GetJ "$v/$postId/comments?fields=id,message,created_time,from,comments{from}&filter=toplevel&limit=50&access_token=$pt").data } catch { Log ("FB read ERR $postId " + (E $_)); continue }
  foreach ($c in $cs) {
    if ($replied -ge $maxPerRun) { break }
    if ($done[$c.id]) { continue }
    if ($c.from -and $c.from.id -eq $pageId) { $done[$c.id] = $true; continue }
    if ([datetime]$c.created_time -lt $cutoff) { continue }
    if ($c.comments -and ($c.comments.data | Where-Object { $_.from.id -eq $pageId })) { $done[$c.id] = $true; continue }
    if (ShouldSkip $c.message) { continue }
    $msg = PickReply $c.message
    $who = if ($c.from) { $c.from.name } else { "someone" }
    if ($DryRun) { Log ("DRY FB [$($fbPosts[$postId])] ${who}: $($c.message)  ->  $msg"); $replied++; continue }
    try { PostUtf8 "$v/$($c.id)/comments" @{ message = $msg; access_token = $pt } | Out-Null; $done[$c.id] = $true; $replied++; Log ("FB [$($fbPosts[$postId])] ${who}: $($c.message)"); Start-Sleep 4 }
    catch { Log ("FB reply ERR $who " + (E $_)) }
  }
}

if (-not $DryRun) { ($done.Keys | ConvertTo-Json) | Set-Content $state -Encoding UTF8 }
Log ("RUN DONE. " + ($(if($DryRun){"would reply "}else{"replied "})) + $replied)
