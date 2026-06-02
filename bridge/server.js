const express = require('express');
const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const fs = require('fs');

const PORT = process.env.PORT || 8080;
const BOT_URL = process.env.BOT_URL || 'http://localhost:10000';
const SESSION_DIR = './session';

if (!fs.existsSync(SESSION_DIR)) {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
}

const app = express();
app.use(express.json());

let sock = null;
let qrData = null;
let status = 'starting';
let reconnectTimer = null;

async function connect() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    browser: ['ZAPTURBO', 'Chrome', '1.0'],
    syncFullHistory: false,
    markOnlineOnConnect: false,
    emitOwnEvents: false,
  });

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      qrData = qr;
      status = 'qr';
      qrcode.generate(qr, { small: true });
      console.log('[QR] Escaneie com WhatsApp');
    }

    if (connection === 'open') {
      status = 'connected';
      qrData = null;
      console.log('[OK] WhatsApp Conectado!');
      if (sock.user) console.log('[+] Número:', sock.user.id);
      if (reconnectTimer) clearTimeout(reconnectTimer);
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      status = 'disconnected';
      console.log('[!] Desconectado, reconectando em 10s...');

      if (reason === DisconnectReason.loggedOut) {
        console.log('[!] Sessão expirada, limpando...');
        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
        fs.mkdirSync(SESSION_DIR, { recursive: true });
      }

      reconnectTimer = setTimeout(() => connect(), 10000);
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (m) => {
    const msg = m.messages[0];
    if (!msg || msg.key.fromMe) return;

    const phone = msg.key.remoteJid.replace('@s.whatsapp.net', '').replace('@c.us', '');
    const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
    const name = msg.pushName || 'Cliente';
    if (!text) return;

    console.log(`[MSG] ${phone}: ${text.substring(0, 60)}`);

    try {
      await fetch(`${BOT_URL}/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, text, name }),
        signal: AbortSignal.timeout(5000),
      });
    } catch (e) {
      console.error('[WEBHOOK]', e.message);
    }
  });
}

app.get('/', (req, res) => {
  res.json({ status, qr: qrData, phone: sock?.user?.id || null });
});

app.get('/qr', (req, res) => {
  res.json({ status, qr: qrData });
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body || {};
  if (!to || !text) return res.status(400).json({ error: 'faltando to/text' });
  try {
    const jid = `${to.replace(/\D/g, '')}@s.whatsapp.net`;
    await sock.sendMessage(jid, { text });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Bridge] Porta ${PORT}, webhook -> ${BOT_URL}/webhook`);
  connect();
});
