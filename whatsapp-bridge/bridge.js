const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const path = require('path');
const fs = require('fs');

const PORT = process.env.PORT || 8080;
const BOT_WEBHOOK_URL = process.env.BOT_WEBHOOK_URL || 'http://localhost:10000/webhook';
const SESSION_DIR = './session';

if (!fs.existsSync(SESSION_DIR)) {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
}

const app = express();
app.use(express.json());

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
  puppeteer: {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
      '--disable-gpu',
    ],
  },
  webVersionCache: {
    type: 'remote',
    remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
  },
});

let qrCodeData = null;
let connectionState = 'disconnected';

client.on('qr', (qr) => {
  qrCodeData = qr;
  qrcode.generate(qr, { small: true });
  connectionState = 'awaiting_qr';
  console.log('[QR] New QR code generated. Scan with WhatsApp.');
});

client.on('ready', () => {
  connectionState = 'connected';
  qrCodeData = null;
  console.log('[CONNECTED] WhatsApp connected!');
  console.log(`[PHONE] ${client.info.wid.user}`);
});

client.on('disconnected', (reason) => {
  connectionState = 'disconnected';
  console.log(`[DISCONNECTED] Reason: ${reason}`);
  setTimeout(() => client.initialize(), 10000);
});

client.on('message', async (message) => {
  if (message.fromMe) return;

  const phone = message.from.replace('@c.us', '').replace('@s.whatsapp.net', '');
  const body = message.body;
  const name = message._data?.notifyName || 'Cliente';

  console.log(`[MSG] ${phone} (${name}): ${body.substring(0, 60)}`);

  try {
    const resp = await fetch(BOT_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'message.create',
        data: {
          key: { remoteJid: message.from },
          message: { conversation: body },
          pushName: name,
        },
      }),
      signal: AbortSignal.timeout(10000),
    });
  } catch (err) {
    console.error('[WEBHOOK ERROR]', err.message);
  }
});

app.get('/', (req, res) => {
  res.json({
    status: connectionState,
    qr: qrCodeData,
    phone: client.info?.wid?.user || null,
  });
});

app.get('/qr', (req, res) => {
  if (qrCodeData) {
    res.json({ qr: qrCodeData, state: connectionState });
  } else if (connectionState === 'connected') {
    res.json({ qr: null, state: 'connected', message: 'Already connected!' });
  } else {
    res.json({ qr: null, state: connectionState, message: 'Starting up, check logs for QR...' });
  }
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body;
  if (!to || !text) {
    return res.status(400).json({ error: 'Missing "to" or "text"' });
  }

  try {
    const chatId = `${to.replace(/\D/g, '')}@c.us`;
    await client.sendMessage(chatId, text);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send-image', async (req, res) => {
  const { to, imageUrl, caption } = req.body;
  if (!to || !imageUrl) {
    return res.status(400).json({ error: 'Missing "to" or "imageUrl"' });
  }

  try {
    const chatId = `${to.replace(/\D/g, '')}@c.us`;
    const media = await MessageMedia.fromUrl(imageUrl);
    await client.sendMessage(chatId, media, { caption: caption || '' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[BRIDGE] Running on port ${PORT}`);
  console.log(`[BRIDGE] Webhook: ${BOT_WEBHOOK_URL}`);
});

console.log('[BRIDGE] Initializing WhatsApp client...');
client.initialize();
