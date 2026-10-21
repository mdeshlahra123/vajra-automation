# Daily health check. Prints one line per problem (empty output = all good).
$base = $PSScriptRoot
$q = Get-Content "$base/queue.json" -Raw | ConvertFrom-Json
$pending = @($q.posts | Where-Object { -not $_.posted })
$reels  = @($pending | Where-Object { $_.video }).Count
$images = @($pending | Where-Object { -not $_.video }).Count
if ($reels  -lt 4) { "Queue low: only $reels reel(s) left (morning slot). Add new reels." }
if ($images -lt 4) { "Queue low: only $images post(s) left (night slot). Add new posts." }

$t = $env:META_TOKEN
try {
  $d = (Invoke-RestMethod "https://graph.facebook.com/v24.0/debug_token?input_token=$t&access_token=$t").data
  if (-not $d.is_valid) { "Meta token is INVALID. Posting and replies will fail until it is renewed." }
  foreach ($k in 'expires_at','data_access_expires_at') {
    $x = [long]$d.$k
    if ($x -gt 0) {
      $days = [int](([DateTimeOffset]::FromUnixTimeSeconds($x).UtcDateTime - (Get-Date).ToUniversalTime()).TotalDays)
      if ($days -le 7) { "Meta access ($k) expires in $days day(s). Renew it now." }
    }
  }
} catch { "Could not check the Meta token: $($_.Exception.Message)" }
