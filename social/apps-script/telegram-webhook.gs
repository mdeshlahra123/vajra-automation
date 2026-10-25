/**
 * VAJRA Telegram approvals (Google Apps Script, free, runs on Google's servers).
 * Instant: Telegram webhook -> Vercel relay (website/api/tg.js) -> doPost(). Fallback: every minute pollTelegram() reads button taps from Telegram, answers them, and starts GitHub approve.yml (mode=tap).
 * (A Telegram webhook doesn't work with Apps Script: it replies with a 302 redirect, which Telegram treats as a failure.)
 *
 * Script properties: BOT_TOKEN, GH_TOKEN, CHAT_ID (-5041048930). KEY / WEB_APP_URL are no longer needed.
 * Setup: paste this code, save, then run installTrigger() once.
 */
function installTrigger() {
  tg_('deleteWebhook', {});  // polling and webhook can't both be on
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('pollTelegram').timeBased().everyMinutes(1).create();
  Logger.log('Trigger installed. Webhook: ' + tg_('getWebhookInfo', {}).getContentText());
  pollTelegram();
}

var WEB_APP_URL = 'https://script.google.com/macros/s/AKfycbzJVrl3o3KhBbl4m-JmCG1KrFyzM6KwMS6ewMefhrSxEgajLr4dsge30QUtKzJRg-vE/exec';
// Instant mode: Telegram -> https://vajraformwork.vercel.app/api/tg (relay) -> doPost here. Needs this script deployed as a Web app.
function doPost(e) {
  var P = PropertiesService.getScriptProperties();
  if (!e || !e.parameter || e.parameter.s !== P.getProperty('HOOK_SECRET')) return ContentService.createTextOutput('no');
  var u = JSON.parse(e.postData.contents);
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var seen = JSON.parse(P.getProperty('SEEN') || '[]');
    if (seen.indexOf(u.update_id) >= 0) return ContentService.createTextOutput('dup');
    seen.push(u.update_id); P.setProperty('SEEN', JSON.stringify(seen.slice(-50)));
    if (u.callback_query) handleTap_(u.callback_query, P);
    else if (u.message) handleMessage_(u.message, P);
  } finally { lock.releaseLock(); }
  return ContentService.createTextOutput('ok');
}
// Turn the webhook on when the web app exists; turn it off (back to polling) if Telegram reports errors.
function webhook_(P) {
  // getService().getUrl() can return an address that 404s for Telegram, so use the fixed Web app URL
  var url = (P.getProperty('WEB_APP_URL') || WEB_APP_URL).trim();
  if (!/^https:\/\/script\.google\.com\/macros\/s\/[\w-]+\/exec$/.test(url)) return false;
  if (P.getProperty('HOOK') === url) {
    if (Date.now() - Number(P.getProperty('HOOK_CHECK') || 0) < 10 * 60 * 1000) return true;
    P.setProperty('HOOK_CHECK', String(Date.now()));
    var info = JSON.parse(tg_('getWebhookInfo', {}).getContentText()).result || {};
    if (info.url && info.url.indexOf(encodeURIComponent(url)) >= 0 &&
        !(info.last_error_date && Date.now() / 1000 - info.last_error_date < 600 && info.pending_update_count > 0)) return true;
    Logger.log('webhook broken, back to polling: ' + JSON.stringify(info));
    tg_('deleteWebhook', {}); P.setProperty('HOOK', 'off:' + Date.now()); return false;
  }
  if (/^off:/.test(P.getProperty('HOOK') || '') && Date.now() - Number(P.getProperty('HOOK').slice(4)) < 3600 * 1000) return false;
  var secret = P.getProperty('HOOK_SECRET') || Utilities.getUuid().replace(/-/g, '');
  P.setProperty('HOOK_SECRET', secret);
  var r = JSON.parse(tg_('setWebhook', { url: 'https://vajraformwork.vercel.app/api/tg?to=' + encodeURIComponent(url),
    secret_token: secret, allowed_updates: ['callback_query', 'message'] }).getContentText());
  Logger.log('setWebhook: ' + JSON.stringify(r));
  if (r.ok) { P.setProperty('HOOK', url); P.setProperty('HOOK_CHECK', String(Date.now())); }
  return !!r.ok;
}
function pollTelegram() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;  // previous run still busy
  try {
    var P = PropertiesService.getScriptProperties();
    if (!webhook_(P)) {
      var offset = Number(P.getProperty('OFFSET') || 0);
      var res = JSON.parse(tg_('getUpdates', { offset: offset, timeout: 0, allowed_updates: ['callback_query', 'message'] }).getContentText());
      if (!res.ok) { Logger.log('getUpdates failed: ' + JSON.stringify(res)); return; }
      res.result.forEach(function (u) {
        offset = u.update_id + 1;
        P.setProperty('OFFSET', String(offset));  // save first, so nothing is handled twice
        if (u.callback_query) handleTap_(u.callback_query, P);
        else if (u.message) handleMessage_(u.message, P);
      });
    }
    // no /reel? make the reel automatically 20 minutes after the last clip
    var clips = JSON.parse(P.getProperty('CLIPS') || '[]');
    if (clips.length && Date.now() - clips[clips.length - 1].t > 20 * 60 * 1000) {
      var note = clips.map(function (c) { return c.note || ''; }).filter(String).join('. ');
      startReel_(clips, note, clips[0].who, P, P.getProperty('CHAT_ID'));
    }
  } finally { lock.releaseLock(); }
}

function handleTap_(cq, P) {
  if (!cq.message) return;
  var chat = String(cq.message.chat.id);
  if (chat !== P.getProperty('CHAT_ID')) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Unknown chat' }); return; }
  var data = cq.data || '';
  if (data === 'done' || data.indexOf('test:') === 0) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Already handled.' }); return; }
  var who = cq.from.first_name || 'someone';
  // storyboard buttons: Banao = make the reel from the reviewed plan, Chhodo = drop it
  if (data.indexOf('mk:') === 0 || data.indexOf('sb-no:') === 0) {
    var make = data.indexOf('mk:') === 0, sid = data.split(':')[1];
    tg_('answerCallbackQuery', { callback_query_id: cq.id, text: make ? '▶️ Ban raha hai…' : 'Chhod diya' });
    tg_('editMessageReplyMarkup', { chat_id: chat, message_id: cq.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: make ? '▶️ Ban raha hai (' + who + '), 10-15 min' : '❌ Chhod diya (' + who + ')', callback_data: 'done' }]] } });
    if (make) ghRun_('make-reel.yml', { mode: 'build', id: sid }, P, chat);
    return;
  }
  var approve = data.indexOf('ok:') === 0;
  tg_('answerCallbackQuery', { callback_query_id: cq.id, text: (approve ? '✅ Approve' : '❌ Reject') + ' received, processing…' });
  tg_('editMessageReplyMarkup', { chat_id: chat, message_id: cq.message.message_id,
    reply_markup: { inline_keyboard: [[{ text: '⏳ ' + (approve ? 'Approving' : 'Rejecting') + '… (' + who + ')', callback_data: 'done' }]] } });
  var r = UrlFetchApp.fetch('https://api.github.com/repos/mdeshlahra123/vajra-automation/actions/workflows/approve.yml/dispatches', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + P.getProperty('GH_TOKEN'), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    payload: JSON.stringify({ ref: 'main', inputs: { mode: 'tap', id: data + '|' + who + '|' + cq.message.message_id } })
  });
  if (r.getResponseCode() !== 204) {
    var id = data.split(':')[1];
    tg_('editMessageReplyMarkup', { chat_id: chat, message_id: cq.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: '✅ Approve', callback_data: 'ok:' + id }, { text: '❌ Reject', callback_data: 'no:' + id }]] } });
    tg_('sendMessage', { chat_id: chat, text: '⚠️ Could not start GitHub (' + r.getResponseCode() + '). Please tap again in a minute.' });
  }
}

// Clips: videos sent to the group are collected; "/reel <note>" turns them into a reel (GitHub make-real.yml).
// Instant answer for "aaj/kal/next konsi reel/post" from the public next.json (no brain run needed).
function fastNext_(q, chat, replyTo) {
  var s = q.toLowerCase();
  // Only a plain "which reel/post goes next" question. Anything else (problems, why/how, audio, changes) goes to the brain.
  if (s.length > 70) return false;
  if (/(nahi|nhi|kyu|kyon|why|how|kaise|audio|awaaz|aawaz|sound|problem|issue|error|galat|wrong|change|badlo|hatao|mat|not|dikkat|kharab|\?.*\?)/.test(s)) return false;
  if (!/(konsi|kaunsi|kon si|kaun si|kya|which|what|batao|dikhao|show)/.test(s)) return false;
  if (!/(reel|post|video|photo|image)/.test(s) || !/(aaj|aj\b|kal|next|agla|agli|today|tomorrow|upcoming|aane wali|jayegi|jaegi|dalne|daalne)/.test(s)) return false;
  var r = UrlFetchApp.fetch('https://vajraformwork.vercel.app/social/next.json?t=' + Date.now(), { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) return false;
  var d = JSON.parse(r.getContentText());
  var now = new Date(Date.now() + 5.5 * 3600 * 1000);
  var today = now.toISOString().slice(0, 10), hm = now.toISOString().slice(11, 16);
  var tom = new Date(now.getTime() + 86400000).toISOString().slice(0, 10);
  var wantImg = /(photo|image|post\b|shaam|evening)/.test(s) && !/reel|video/.test(s);
  var list = (wantImg ? d.images : d.reels).filter(function (x) { return x.date > today || (x.date === today && x.time > hm); });
  if (!list.length) return false;
  var wantKal = /(kal|tomorrow)/.test(s) && !/aaj|today/.test(s);
  var item = wantKal ? (list.filter(function (x) { return x.date === tom; })[0] || list[1] || list[0]) : list[0];
  var when = (item.date === today ? 'Aaj' : item.date === tom ? 'Kal' : item.date) + ' ' + item.time;
  var cap = (wantImg ? '🖼 ' : '🎬 ') + when + ' ko ye jayegi:\n' + (item.hook || item.id);
  if (list[1] && item === list[0]) cap += '\n\nUske baad: ' + (list[1].hook || list[1].id).slice(0, 80);
  var res = tg_(wantImg ? 'sendPhoto' : 'sendVideo', wantImg ? { chat_id: chat, photo: item.url, caption: cap, reply_to_message_id: replyTo }
    : { chat_id: chat, video: item.url + '?v=' + d.made, caption: cap + '\n🔊 Awaaz ke liye video kholo / tap karo', reply_to_message_id: replyTo, supports_streaming: true });
  if (res.getResponseCode() !== 200) tg_('sendMessage', { chat_id: chat, text: cap + '\n' + item.url, reply_to_message_id: replyTo });
  return true;
}

function handleMessage_(m, P) {
  var chat = String(m.chat.id);
  if (chat !== P.getProperty('CHAT_ID')) return;
  var who = (m.from && m.from.first_name) || 'someone';
  var vid = m.video || (m.document && /^video\//.test(m.document.mime_type || '') ? m.document : null);
  var clips = JSON.parse(P.getProperty('CLIPS') || '[]').filter(function (c) { return Date.now() - c.t < 12 * 3600 * 1000; });
  if (vid) {
    if ((vid.file_size || 0) > 20 * 1024 * 1024) {
      tg_('sendMessage', { chat_id: chat, reply_to_message_id: m.message_id,
        text: '⚠️ Ye clip ' + Math.round(vid.file_size / 1048576) + ' MB hai. Bot sirf 20 MB tak le sakta hai. Chhota clip bhejo (30-40 sec), ya "as file" ki jagah normal video bhejo.' });
      return;
    }
    clips.push({ id: vid.file_id, who: who, t: Date.now(), note: (m.caption || '').replace(/^\/reel(@\w+)?/i, '').trim() });
    P.setProperty('CLIPS', JSON.stringify(clips));
    tg_('sendMessage', { chat_id: chat, reply_to_message_id: m.message_id,
      text: '📥 Clip ' + clips.length + ' mila. Aur clips ho to bhejo. 20 min tak naya clip nahi aaya to reel apne aap banegi. Jaldi chahiye to likho: /reel aur ek line ki note.' });
    return;
  }
  var text = (m.text || '').trim();
  // reply to a storyboard = changes for that reel plan
  var rt = m.reply_to_message && (m.reply_to_message.text || m.reply_to_message.caption || '');
  var sb = rt && rt.match(/SB:(reel-ai-[\w-]+)/);
  if (text && text.charAt(0) !== '/' && sb) {
    tg_('sendMessage', { chat_id: chat, reply_to_message_id: m.message_id, text: '✏️ Samajh gaya, naya plan bana raha hun (2-3 min).' });
    ghRun_('make-reel.yml', { mode: 'revise', id: sb[1], feedback: text.slice(0, 900) }, P, chat);
    return;
  }
  if (text && text.charAt(0) !== '/' && m.reply_to_message && m.reply_to_message.from && m.reply_to_message.from.is_bot) text = '/ask ' + text;
  if (/^\/ask(@\w+)?\b/i.test(text)) {
    var q = text.replace(/^\/ask(@\w+)?/i, '').trim();
    if (!q) { tg_('sendMessage', { chat_id: chat, text: 'Likho: /ask aur apna kaam, jaise: /ask aaj ke ads kaise chale?' }); return; }
    if (fastNext_(q, chat, m.message_id)) return;
    var a = UrlFetchApp.fetch('https://api.github.com/repos/mdeshlahra123/vajra-automation/actions/workflows/ask.yml/dispatches', {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      headers: { Authorization: 'Bearer ' + P.getProperty('GH_TOKEN'), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
      payload: JSON.stringify({ ref: 'main', inputs: { task: (m.reply_to_message ? '[Replying to this bot message: ' + String(m.reply_to_message.text || m.reply_to_message.caption || '(media)').slice(0, 300) + '] ' : '') + q.slice(0, 600), who: who } })
    });
    tg_('sendMessage', { chat_id: chat, reply_to_message_id: m.message_id,
      text: a.getResponseCode() === 204 ? '🧠 Dekh raha hun... ~30 sec mein jawab.' : '⚠️ Brain start nahi hua (' + a.getResponseCode() + ').' });
    return;
  }
  if (!/^\/reel(@\w+)?\b/i.test(text)) return;
  if (!clips.length) { tg_('sendMessage', { chat_id: chat, text: 'Pehle clips bhejo, phir /reel likho.' }); return; }
  var note = [text.replace(/^\/reel(@\w+)?/i, '').trim()].concat(clips.map(function (c) { return c.note || ''; })).filter(String).join('. ');
  startReel_(clips, note, who, P, chat);
}

function startReel_(clips, note, who, P, chat) {
  var r = UrlFetchApp.fetch('https://api.github.com/repos/mdeshlahra123/vajra-automation/actions/workflows/make-real.yml/dispatches', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + P.getProperty('GH_TOKEN'), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    payload: JSON.stringify({ ref: 'main', inputs: { clips: clips.map(function (c) { return c.id; }).join(','), note: note.slice(0, 500), who: who } })
  });
  if (r.getResponseCode() === 204) {
    P.setProperty('CLIPS', '[]');
    tg_('sendMessage', { chat_id: chat, text: '🎬 ' + clips.length + ' clips se reel ban rahi hai. ~10 min mein yahin approval ke liye aayegi.' });
  } else {
    // keep the clips; push the auto-start 20 minutes later instead of retrying every minute
    clips.forEach(function (c) { c.t = Date.now(); });
    P.setProperty('CLIPS', JSON.stringify(clips));
    tg_('sendMessage', { chat_id: chat, text: '⚠️ Reel start nahi hui (GitHub ' + r.getResponseCode() + '). 20 min baad apne aap dobara try hoga, ya /reel likho.' });
  }
}

function ghRun_(wf, inputs, P, chat) {
  var r = UrlFetchApp.fetch('https://api.github.com/repos/mdeshlahra123/vajra-automation/actions/workflows/' + wf + '/dispatches', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + P.getProperty('GH_TOKEN'), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    payload: JSON.stringify({ ref: 'main', inputs: inputs })
  });
  if (r.getResponseCode() !== 204) tg_('sendMessage', { chat_id: chat, text: '⚠️ GitHub start nahi hua (' + r.getResponseCode() + '). Thodi der baad dobara try karo.' });
}

function tg_(method, params) {
  return UrlFetchApp.fetch('https://api.telegram.org/bot' + PropertiesService.getScriptProperties().getProperty('BOT_TOKEN') + '/' + method,
    { method: 'post', contentType: 'application/json', payload: JSON.stringify(params), muteHttpExceptions: true });
}
