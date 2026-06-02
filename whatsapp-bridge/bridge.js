const express = require('express');
const { makeWASocket, useMultiFileAuthState, makeCacheableSignalKeyStore, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const BOT_WEBHOOK_URL = process.env.BOT_WEBHOOK_URL || 'http://localhost:10000/webhook';
const SESSION_DIR = './session';

if (!fs.existsSync(SESSION_DIR)) {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
}

const app = express();
app.use(express.json());

let sock = null;
let qrCodeData = null;
let connectionState = 'disconnected';

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' })),
    },
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
    browser: ['ZAPTURBO', 'Chrome', '1.0.0'],
  });

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      qrCodeData = qr;
      qrcode.generate(qr, { small: true });
      connectionState = 'awaiting_qr';
      console.log('[QR] New QR code generated. Scan with WhatsApp.');
    }

    if (connection === 'open') {
      connectionState = 'connected';
      qrCodeData = null;
      console.log('[CONNECTED] WhatsApp connected!');
      console.log(`[PHONE] ${sock.user.id}`);
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      connectionState = 'disconnected';
      console.log(`[DISCONNECTED] Reason: ${DisconnectReason[reason] || reason}`);

      if (reason === DisconnectReason.loggedOut) {
        console.log('[LOGGED OUT] Clearing session...');
        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
        fs.mkdirSync(SESSION_DIR, { recursive: true });
      }

      setTimeout(() => start(), 5000);
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (msg) => {
    const message = msg.messages[0];
    if (!message || message.key.fromMe) return;
    if (!message.message?.conversation && !message.message?.extendedTextMessage) return;

    const phone = message.key.remoteJid.replace('@s.whatsapp.net', '').replace('@c.us', '');
    const body = message.message?.conversation || message.message?.extendedTextMessage?.text || '';
    const name = message.pushName || 'Cliente';

    console.log(`[MSG] ${phone} (${name}): ${body.substring(0, 60)}`);

    try {
      const resp = await fetch(BOT_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: 'message.create',
          data: {
            key: { remoteJid: message.key.remoteJid },
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
}

app.get('/', (req, res) => {
  res.json({
    status: connectionState,
    qr: qrCodeData,
    phone: sock?.user?.id || null,
  });
});

app.get('/qr', (req, res) => {
  if (qrCodeData) {
    res.json({ qr: qrCodeData, state: connectionState });
  } else {
    res.json({ qr: null, state: connectionState, message: 'Already connected or starting...' });
  }
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body;
  if (!to || !text) {
    return res.status(400).json({ error: 'Missing "to" or "text"' });
  }

  try {
    const chatId = `${to.replace(/\D/g, '')}@s.whatsapp.net`;
    await sock.sendMessage(chatId, { text });
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
    const chatId = `${to.replace(/\D/g, '')}@s.whatsapp.net`;
    const response = await fetch(imageUrl);
    const buffer = await response.arrayBuffer();
    const base64 = Buffer.from(buffer).toString('base64');
    const mime = response.headers.get('content-type') || 'image/jpeg';

    await sock.sendMessage(chatId, {
      image: Buffer.from(base64, 'base64'),
      caption: caption || '',
      mimetype: mime,
    });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

start();

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[BRIDGE] Running on port ${PORT}`);
  console.log(`[BRIDGE] Webhook: ${BOT_WEBHOOK_URL}`);
});
