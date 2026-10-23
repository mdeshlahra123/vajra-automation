/**
 * VAJRA Telegram approvals (Google Apps Script, free, runs on Google's servers).
 * Every minute pollTelegram() reads button taps from Telegram, answers them, and starts GitHub approve.yml (mode=tap).
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

function pollTelegram() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;  // previous run still busy
  try {
    var P = PropertiesService.getScriptProperties();
    var offset = Number(P.getProperty('OFFSET') || 0);
    var res = JSON.parse(tg_('getUpdates', { offset: offset, timeout: 0, allowed_updates: ['callback_query'] }).getContentText());
    if (!res.ok) { Logger.log('getUpdates failed: ' + JSON.stringify(res)); return; }
    res.result.forEach(function (u) {
      offset = u.update_id + 1;
      P.setProperty('OFFSET', String(offset));  // save first, so a tap is never handled twice
      if (u.callback_query) handleTap_(u.callback_query, P);
    });
  } finally { lock.releaseLock(); }
}

function handleTap_(cq, P) {
  if (!cq.message) return;
  var chat = String(cq.message.chat.id);
  if (chat !== P.getProperty('CHAT_ID')) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Unknown chat' }); return; }
  var data = cq.data || '';
  if (data === 'done' || data.indexOf('test:') === 0) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Already handled.' }); return; }
  var who = cq.from.first_name || 'someone';
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

function tg_(method, params) {
  return UrlFetchApp.fetch('https://api.telegram.org/bot' + PropertiesService.getScriptProperties().getProperty('BOT_TOKEN') + '/' + method,
    { method: 'post', contentType: 'application/json', payload: JSON.stringify(params), muteHttpExceptions: true });
}
