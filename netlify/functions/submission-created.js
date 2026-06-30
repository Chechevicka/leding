const https = require('https');

exports.handler = async function(event) {
  // Netlify triggers this function automatically on every form submission
  const { payload } = JSON.parse(event.body);
  const { name, org, email, type, message, tier } = payload.data || {};

  const text = [
    '🔔 Новий запит на партнерство!',
    '',
    `👤 Ім'я: ${name || '—'}`,
    `🏢 Організація: ${org || '—'}`,
    `📧 Email: ${email || '—'}`,
    `🤝 Напрямок: ${type || tier || '—'}`,
    `📝 Повідомлення: ${message || '—'}`
  ].join('\n');

  // ---- Telegram ----
  const tgToken = process.env.TELEGRAM_BOT_TOKEN;
  const tgChatId = process.env.TELEGRAM_CHAT_ID;

  if (tgToken && tgChatId) {
    try {
      await httpPost(`https://api.telegram.org/bot${tgToken}/sendMessage`, {
        chat_id: tgChatId,
        text: text
      });
      console.log('✅ Telegram sent');
    } catch (err) {
      console.error('❌ Telegram error:', err.message);
    }
  } else {
    console.log('⚠️ Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)');
  }

  return { statusCode: 200, body: 'OK' };
};

function httpPost(url, data) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(data);
    const parsed = new URL(url);
    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    };
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', d => chunks += d);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(chunks);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${chunks}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}
