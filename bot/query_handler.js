const path = require('path');
const fs = require('fs');

// Load .env explicitly — read the file ourselves so it works regardless of
// working directory or dotenv version quirks.
(function loadEnv() {
  const envPath = path.join(__dirname, '../.env');
  if (!fs.existsSync(envPath)) return;
  const lines = fs.readFileSync(envPath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, '');
    if (!process.env[key]) process.env[key] = val;
  }
})();

const Anthropic = require('@anthropic-ai/sdk');
const { toolDefinitions, executeTool } = require('./tools');

// Lazy-initialised so the key is definitely in process.env before use
let _anthropic = null;
function getClient() {
  if (!_anthropic) {
    if (!process.env.ANTHROPIC_API_KEY) throw new Error('ANTHROPIC_API_KEY not set');
    _anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }
  return _anthropic;
}

const SYSTEM_PROMPT = `Você é o Brazuka Bot, assistente oficial do BRAZUKA & RECEBA FC.
Responda sempre em português brasileiro, de forma direta e com bom humor.
Use emojis com moderação. Para perguntas de stats, use as tools disponíveis.
Se não souber a resposta ou os dados não existirem, diga isso de forma clara.
Mantenha respostas curtas — isso é um chat de WhatsApp, não um relatório.

Ao chamar tools que recebem nome de jogador, sempre use o nome canônico completo.
Nomes canônicos dos jogadores principais:
- "arthur" ou "eu" → "Arthur Mendes"
- "kuster" → "Kuster"
- "daniel" → "Daniel Tedesco"
- "caio" → "Caio Scofield"
- "rafael" ou "rato" → "Rafael Franco"
- "pedro" → "Pedro Nakamura"
- "lucas" → "Lucas Claro"
- "marcelo" → verifique contexto (Marcelo D ou Marcelo Mazzafera)
- "guilherme" → verifique contexto (Kuster, Guilherme Pereira ou Guilherme Souza)
- "cleiton" → verifique contexto (Cleiton Castro ou Cleiton Moura)
- "joao" → verifique contexto (Joao Barros ou Joao Pinto)
- "igor" → verifique contexto (Igor Moreira ou Igor Seattle)`;

/**
 * Handles a query from the WhatsApp group.
 * Uses Claude with function calling to fetch the right data from Supabase.
 *
 * @param {string} query - The user's question (trigger prefix already stripped)
 * @returns {Promise<string>} - The reply to send back
 */
async function handleQuery(query) {
  const anthropic = getClient();
  const messages = [{ role: 'user', content: query }];

  // Agentic loop: keep going until Claude sends a final text response
  while (true) {
    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-5',
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      tools: toolDefinitions,
      messages,
    });

    // Add Claude's response to the message history
    messages.push({ role: 'assistant', content: response.content });

    if (response.stop_reason === 'end_turn') {
      const textBlock = response.content.find((b) => b.type === 'text');
      return textBlock ? textBlock.text : '🤔 Não consegui formular uma resposta.';
    }

    if (response.stop_reason === 'tool_use') {
      // Execute all tool calls in parallel
      const toolUseBlocks = response.content.filter((b) => b.type === 'tool_use');
      const toolResults = await Promise.all(
        toolUseBlocks.map(async (block) => {
          console.log(`[TOOL] Chamando ${block.name}(${JSON.stringify(block.input)})`);
          try {
            const result = await executeTool(block.name, block.input);
            console.log(`[TOOL] Resultado: ${JSON.stringify(result).slice(0, 120)}`);
            return {
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify(result),
            };
          } catch (err) {
            console.error(`[TOOL] Erro em ${block.name}:`, err.message);
            return {
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify({ error: err.message }),
              is_error: true,
            };
          }
        })
      );

      messages.push({ role: 'user', content: toolResults });
      continue;
    }

    console.warn('[WARN] Stop reason inesperado:', response.stop_reason);
    break;
  }

  return '😅 Algo deu errado. Tenta de novo!';
}

module.exports = { handleQuery };
