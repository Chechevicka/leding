const https = require('https');
const nodemailer = require('nodemailer');

exports.handler = async function(event) {
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
  }

  // ---- Email via SMTP ----
  const smtpHost = process.env.SMTP_HOST;
  const smtpPort = process.env.SMTP_PORT || '587';
  const smtpUser = process.env.SMTP_USER;
  const smtpPass = process.env.SMTP_PASSWORD;
  const toEmail = process.env.TO_EMAIL || 'nb@kosmostabir.org';

  if (smtpHost && smtpUser && smtpPass) {
    try {
      const transporter = nodemailer.createTransport({
        host: smtpHost,
        port: parseInt(smtpPort),
        secure: parseInt(smtpPort) === 465,
        auth: {
          user: smtpUser,
          pass: smtpPass
        }
      });

      const htmlBody = `
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #1a3c34; border-bottom: 2px solid #1a3c34; padding-bottom: 8px;">Нова заявка на партнерство</h2>
            <p><strong>Ім'я контактної особи:</strong> ${escHtml(name)}</p>
            <p><strong>Організація / Компанія:</strong> ${escHtml(org)}</p>
            <p><strong>Електронна пошта:</strong> <a href="mailto:${escHtml(email)}">${escHtml(email)}</a></p>
            <p><strong>Напрямок співпраці:</strong> ${escHtml(type || tier)}</p>
            <div style="background: #f7f6f2; padding: 15px; border-radius: 6px; border: 1px solid #e5e5e5; margin-top: 15px;">
              <strong>Повідомлення / Пропозиція:</strong><br>
              ${escHtml(message).replace(/\n/g, '<br>')}
            </div>
          </body>
        </html>
      `;

      await transporter.sendMail({
        from: smtpUser,
        to: toEmail,
        subject: `Нова заявка на партнерство: ${name || '—'} (${org || '—'})`,
        html: htmlBody
      });
      console.log('✅ Email sent to', toEmail);
    } catch (err) {
      console.error('❌ Email error:', err.message);
    }
  }

  return { statusCode: 200, body: 'OK' };
};

function escHtml(str) {
  if (!str) return '—';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

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
