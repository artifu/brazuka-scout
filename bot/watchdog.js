// Watchdog: spawns bot/index.js and restarts it if it hangs at startup
// (wwebjs require sometimes hangs due to puppeteer cosmiconfig filesystem search)

const { spawn } = require('child_process');
const path = require('path');

const READY_TIMEOUT_MS = 45000; // 45s to reach [READY]
const RESTART_DELAY_MS = 5000;
const BOT_SCRIPT = path.join(__dirname, 'index.js');
const CWD = path.join(__dirname, '..');

let attempt = 0;

function start() {
  attempt++;
  console.log(`[WATCHDOG] Iniciando bot (tentativa #${attempt})...`);

  const proc = spawn(process.execPath, [BOT_SCRIPT], {
    cwd: CWD,
    stdio: ['inherit', 'pipe', 'pipe'],
    env: { ...process.env },
  });

  let isReady = false;

  // Forward stdout/stderr and watch for [READY]
  proc.stdout.on('data', (data) => {
    process.stdout.write(data);
    if (!isReady && data.toString().includes('[READY]')) {
      isReady = true;
      clearTimeout(timeout);
      console.log('[WATCHDOG] Bot chegou ao estado READY. Monitorando...');
    }
  });
  proc.stderr.on('data', (data) => process.stderr.write(data));

  // Kill if [READY] never arrives within timeout
  const timeout = setTimeout(() => {
    if (!isReady) {
      console.log(`[WATCHDOG] Bot travou na inicialização (${READY_TIMEOUT_MS / 1000}s sem [READY]). Reiniciando...`);
      proc.kill('SIGKILL');
    }
  }, READY_TIMEOUT_MS);

  proc.on('exit', (code, signal) => {
    if (isReady) clearTimeout(timeout);
    console.log(`[WATCHDOG] Bot encerrou (code=${code} signal=${signal}). Reiniciando em ${RESTART_DELAY_MS / 1000}s...`);
    setTimeout(start, RESTART_DELAY_MS);
  });

  proc.on('error', (err) => {
    clearTimeout(timeout);
    console.error('[WATCHDOG] Erro ao iniciar bot:', err.message);
    setTimeout(start, RESTART_DELAY_MS);
  });
}

start();
