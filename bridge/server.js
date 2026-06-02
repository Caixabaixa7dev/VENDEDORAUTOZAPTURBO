const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
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

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
  puppeteer: {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
    ],
  },
});

let qrData = null;
let status = 'starting';

client.on('qr', (qr) => {
  qrData = qr;
  status = 'qr';
  qrcode.generate(qr, { small: true });
  console.log('[QR] Scan with WhatsApp!');
});

client.on('ready', () => {
  status = 'connected';
  qrData = null;
  console.log('[OK] WhatsApp Conectado!');
  console.log(`[+] Número: ${client.info.wid.user}`);
});

client.on('disconnected', (reason) => {
  status = 'disconnected';
  console.log(`[!] Desconectado: ${reason}`);
  setTimeout(() => {
    console.log('[+] Reconectando...');
    client.initialize();
  }, 15000);
});

client.on('message', async (msg) => {
  if (msg.fromMe) return;

  const phone = msg.from.replace('@c.us', '').replace('@s.whatsapp.net', '');
  const text = msg.body;
  const name = msg._data?.notifyName || 'Cliente';

  console.log(`[MSG] ${phone}: ${text.substring(0, 60)}`);

  try {
    await fetch(`${BOT_URL}/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: phone,
        text: text,
        name: name,
      }),
      signal: AbortSignal.timeout(5000),
    });
  } catch (e) {
    console.error(`[WEBHOOK ERRO] ${e.message}`);
  }
});

app.get('/', (req, res) => {
  res.json({ status, qr: qrData, phone: client.info?.wid?.user || null });
});

app.get('/qr', (req, res) => {
  if (qrData) {
    res.json({ qr: qrData, status });
  } else {
    res.json({ qr: null, status });
  }
});

app.post('/send', async (req, res) => {
  const { to, text } = req.body || {};
  if (!to || !text) return res.status(400).json({ error: 'to e text obrigatorios' });

  try {
    const chatId = `${to.replace(/\D/g, '')}@c.us`;
    await client.sendMessage(chatId, text);
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Bridge] Rodando na porta ${PORT}`);
  console.log(`[Bridge] Webhook -> ${BOT_URL}/webhook`);
});

console.log('[Bridge] Iniciando WhatsApp...');
client.initialize();
