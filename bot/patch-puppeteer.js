#!/usr/bin/env node
// Patches puppeteer's getConfiguration.js to skip cosmiconfig filesystem search
// when PUPPETEER_EXECUTABLE_PATH is already set. Without this patch, puppeteer 24.x
// hangs on macOS (iCloud/Spotlight interference with synchronous filesystem traversal).

const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, 'node_modules/puppeteer/lib/cjs/puppeteer/getConfiguration.js');

if (!fs.existsSync(target)) {
  console.log('[patch] getConfiguration.js not found, skipping.');
  process.exit(0);
}

const content = fs.readFileSync(target, 'utf8');
const MARKER = '// PATCH: skip cosmiconfig';

if (content.includes(MARKER)) {
  console.log('[patch] Already patched, skipping.');
  process.exit(0);
}

const FIND = 'const getConfiguration = () => {\n    const result = (0, cosmiconfig_1.cosmiconfigSync)(\'puppeteer\', {';
const REPLACE = `const getConfiguration = () => {
    ${MARKER} filesystem search when executable is already set
    if (process.env['PUPPETEER_EXECUTABLE_PATH']) {
        return {
            logLevel: 'warn',
            defaultBrowser: 'chrome',
            executablePath: process.env['PUPPETEER_EXECUTABLE_PATH'],
            skipDownload: true,
            chrome: { skipDownload: true },
            'chrome-headless-shell': { skipDownload: true },
            firefox: { skipDownload: true },
            cacheDirectory: require('node:path').join(require('node:os').homedir(), '.cache', 'puppeteer'),
            experiments: {},
        };
    }
    const result = (0, cosmiconfig_1.cosmiconfigSync)('puppeteer', {`;

if (!content.includes(FIND)) {
  console.log('[patch] Pattern not found in getConfiguration.js — puppeteer version may have changed.');
  process.exit(0);
}

fs.writeFileSync(target, content.replace(FIND, REPLACE));
console.log('[patch] puppeteer getConfiguration.js patched successfully.');
