/**
 * VAJRA Telegram approvals: instant tap handler (Google Apps Script web app, free, always on).
 * Telegram -> this script (answers the tap at once) -> GitHub approve.yml (mode=tap) does the real work.
 *
 * Script properties (Project Settings > Script properties):
 *   BOT_TOKEN    Telegram bot token from @BotFather
 *   GH_TOKEN     GitHub token that can start workflows in mdeshlahra123/vajra-automation
 *   CHAT_ID      -5041048930
 *   KEY          long random string, also used in the webhook URL
 *   WEB_APP_URL  the /exec URL shown after Deploy > New deployment > Web app
 * Then run setWebhook() once.
 */
function doPost(e) {
  var P = PropertiesService.getScriptProperties();
  if (!e || !e.parameter || e.parameter.k !== P.getProperty('KEY')) return ok_();
  var u = JSON.parse(e.postData.contents);
  // Telegram may resend the same update (Apps Script replies with a redirect); handle each update once.
  var cache = CacheService.getScriptCache();
  if (cache.get('u' + u.update_id)) return ok_();
  cache.put('u' + u.update_id, '1', 21600);

  var cq = u.callback_query;
  if (!cq || !cq.message) return ok_();
  var chat = String(cq.message.chat.id);
  if (chat !== P.getProperty('CHAT_ID')) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Unknown chat' }); return ok_(); }
  var data = cq.data || '';
  if (data === 'done' || data.indexOf('test') === 0) { tg_('answerCallbackQuery', { callback_query_id: cq.id, text: 'Already handled.' }); return ok_(); }

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
    // GitHub didn't accept it: put the buttons back so it can be tapped again
    var id = data.split(':')[1];
    tg_('editMessageReplyMarkup', { chat_id: chat, message_id: cq.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: '✅ Approve', callback_data: 'ok:' + id }, { text: '❌ Reject', callback_data: 'no:' + id }]] } });
    tg_('sendMessage', { chat_id: chat, text: '⚠️ Could not start GitHub (' + r.getResponseCode() + '). Please tap again in a minute.' });
  }
  return ok_();
}

function doGet() { return ContentService.createTextOutput('VAJRA approvals webhook is running.'); }

function setWebhook() {
  var P = PropertiesService.getScriptProperties();
  var url = P.getProperty('WEB_APP_URL') + '?k=' + P.getProperty('KEY');
  Logger.log(tg_('setWebhook', { url: url, allowed_updates: ['callback_query'], max_connections: 5 }).getContentText());
  Logger.log(tg_('getWebhookInfo', {}).getContentText());
}

function ok_() { return ContentService.createTextOutput('ok'); }
function tg_(method, params) {
  return UrlFetchApp.fetch('https://api.telegram.org/bot' + PropertiesService.getScriptProperties().getProperty('BOT_TOKEN') + '/' + method,
    { method: 'post', contentType: 'application/json', payload: JSON.stringify(params), muteHttpExceptions: true });
}
