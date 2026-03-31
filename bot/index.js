console.log('[START] Iniciando bot...');
const path = require('path');
const fs   = require('fs');
const os   = require('os');

// Must set PUPPETEER_EXECUTABLE_PATH BEFORE requiring whatsapp-web.js,
// otherwise puppeteer 18.x hangs trying to locate/download its own Chrome.
function findChromePath() {
  const cacheBase = path.join(os.homedir(), '.cache', 'puppeteer', 'chrome');
  if (!fs.existsSync(cacheBase)) return null;
  for (const build of fs.readdirSync(cacheBase)) {
    const candidates = [
      path.join(cacheBase, build, 'chrome-mac-arm64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing'),
      path.join(cacheBase, build, 'chrome-mac-x64',   'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing'),
      path.join(cacheBase, build, 'chrome-linux', 'chrome'),
    ];
    for (const c of candidates) {
      if (fs.existsSync(c)) return c;
    }
  }
  return null;
}

const chromePath = findChromePath();
if (chromePath) {
  process.env.PUPPETEER_EXECUTABLE_PATH = chromePath;
  console.log('[CHROME] Usando:', chromePath.split('/').slice(-1)[0]);
} else {
  console.warn('[CHROME] Executável não encontrado');
}

require('dotenv').config({ path: path.join(__dirname, '../.env') });
console.log('[LOAD] dotenv ok');
const { Client, LocalAuth } = require('whatsapp-web.js');
console.log('[LOAD] whatsapp-web.js ok');
const qrcode = require('qrcode-terminal');
console.log('[LOAD] qrcode-terminal ok');
const { handleQuery } = require('./query_handler');
console.log('[LOAD] query_handler ok');

// Name of the WhatsApp group to listen to
const GROUP_NAME = 'BRAZUKA & RECEBA FC';

// Prefixes/triggers that cause the bot to respond
const TRIGGERS = ['brzk', 'brazuka'];

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './session' }),
  puppeteer: {
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('\n[QR] Escaneie o QR code abaixo com o WhatsApp Business:\n');
  qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
  console.log('[AUTH] Autenticado com sucesso!');
});

client.on('auth_failure', (msg) => {
  console.error('[AUTH] Falha na autenticação:', msg);
  process.exit(1);
});

client.on('ready', () => {
  console.log(`[READY] Bot conectado. Ouvindo o grupo "${GROUP_NAME}"...`);
});

async function processMessage(msg) {
  try {
    console.log(`[RAW] from=${msg.from} body=${JSON.stringify(msg.body?.slice(0,60))} fromMe=${msg.fromMe}`);
    const chat = await msg.getChat();
    const isGroup = msg.from.endsWith('@g.us');

    // In groups: only respond in the correct group
    if (isGroup && chat.name !== GROUP_NAME) return;

    const body = msg.body.trim();

    // Check if message has a trigger prefix
    const hasTrigger = TRIGGERS.some((t) => body.toLowerCase().startsWith(t));

    // Also respond to direct replies to our bot messages
    const isReply = msg.hasQuotedMsg && (await msg.getQuotedMessage()).fromMe;

    if (!hasTrigger && !isReply) return;

    // Strip the trigger prefix to get the actual query
    let query = body;
    for (const t of TRIGGERS) {
      if (body.toLowerCase().startsWith(t)) {
        query = body.slice(t.length).trim();
        break;
      }
    }

    if (!query && !isReply) {
      await msg.reply(
        '👋 Oi! Manda uma pergunta depois do comando. Ex: `!stats artilheiro`'
      );
      return;
    }

    // If it's a reply with no new text, use the original quoted message as context
    if (!query && isReply) {
      const quoted = await msg.getQuotedMessage();
      query = quoted.body;
    }

    console.log(`[MSG] ${chat.name} | ${msg._data.notifyName}: ${body}`);
    console.log(`[QUERY] Processando: "${query}"`);

    // Show typing indicator while processing
    await chat.sendStateTyping();

    const response = await handleQuery(query);

    await msg.reply(response);
    console.log(`[REPLY] Enviado: ${response.slice(0, 80)}...`);
  } catch (err) {
    console.error('[ERROR] Erro ao processar mensagem:', err);
  }
}

// message_create fires for ALL messages (sent + received).
// Filter fromMe to ignore our own replies and avoid double-processing.
client.on('message_create', (msg) => {
  if (!msg.fromMe) processMessage(msg);
});

client.on('disconnected', (reason) => {
  console.warn('[DISCONNECTED] Bot desconectado:', reason);
  // pm2 will restart the process automatically
  process.exit(1);
});

console.log('[INIT] Chamando client.initialize()...');
client.initialize().catch(err => console.error('[INIT ERROR]', err));
