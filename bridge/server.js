const express = require('express');
const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const fs = require('fs');

const PORT = process.env.PORT || 3000;
const BOT_URL = process.env.BOT_URL || 'http://localhost:10000';
const SESSION_DIR = './session';
const POLL_INTERVAL = 3000;

if (!fs.existsSync(SESSION_DIR)) {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
}

let sock = null;
let status = 'starting';

async function connect() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
    browser: ['ZAPTURBO', 'Chrome', '1.0'],
    syncFullHistory: false,
    markOnlineOnConnect: false,
  });

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      status = 'qr';
      console.log('\n========== QR CODE ==========');
      qrcode.generate(qr, { small: true });
      console.log('==============================\n');
    }

    if (connection === 'open') {
      status = 'connected';
      console.log('\n✅ WhatsApp Conectado!');
      console.log(`📱 Número: ${sock.user?.id}\n`);
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      status = 'disconnected';
      console.log(`\n❌ Desconectado (${reason}). Reconectando em 10s...`);

      if (reason === DisconnectReason.loggedOut) {
        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
        fs.mkdirSync(SESSION_DIR, { recursive: true });
      }

      setTimeout(connect, 10000);
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (m) => {
    const msg = m.messages[0];
    if (!msg || msg.key.fromMe) return;
    if (!msg.message?.conversation && !msg.message?.extendedTextMessage) return;

    const phone = msg.key.remoteJid.replace('@s.whatsapp.net', '').replace('@c.us', '');
    const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
    const name = msg.pushName || 'Cliente';
    if (!text) return;

    console.log(`📩 ${phone}: ${text.substring(0, 80)}`);

    try {
      await fetch(`${BOT_URL}/webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, text, name }),
        signal: AbortSignal.timeout(5000),
      });
    } catch (e) {
      console.error(`⚠️ Webhook: ${e.message}`);
    }
  });
}

async function pollOutbox() {
  if (status !== 'connected' || !sock) return;

  try {
    const phone = sock.user?.id?.split(':')[0];
    if (!phone) return;

    const resp = await fetch(`${BOT_URL}/outbox`, {
      signal: AbortSignal.timeout(3000),
    });

    if (resp.ok) {
      const data = await resp.json();
      if (data.messages && data.messages.length > 0) {
        for (const msg of data.messages) {
          try {
            const jid = `${msg.to.replace(/\D/g, '')}@s.whatsapp.net`;
            await sock.sendMessage(jid, { text: msg.text });
            await fetch(`${BOT_URL}/outbox/${msg.id}/sent`, {
              method: 'POST',
              signal: AbortSignal.timeout(2000),
            });
            console.log(`📤 ${msg.to}: ${msg.text.substring(0, 60)}`);
          } catch (e) {
            console.error(`⚠️ Send error: ${e.message}`);
          }
        }
      }
    }
  } catch (e) {
    // Silently ignore poll errors (bot might be sleeping)
  }
}

setInterval(pollOutbox, POLL_INTERVAL);

console.log('\n🔵 ZAPTURBO WhatsApp Bridge');
console.log('🔄 Iniciando...\n');
connect();
