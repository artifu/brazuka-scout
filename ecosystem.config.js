module.exports = {
  apps: [
    {
      name: 'brazuka-bot',
      script: 'bot/watchdog.js',
      cwd: '/Users/arthur_t_m/Documents/brazuka-scout',
      restart_delay: 5000,
      max_restarts: 20,
      autorestart: true,
      watch: false,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: 'logs/bot-error.log',
      out_file: 'logs/bot-out.log',
      merge_logs: true,
      env: {
        PUPPETEER_EXECUTABLE_PATH: '/Users/arthur_t_m/.cache/puppeteer/chrome/mac_arm-146.0.7680.153/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
      },
    },
  ],
};
