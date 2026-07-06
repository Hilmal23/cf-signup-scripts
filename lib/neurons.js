// Neuron estimation from token usage.
//
// The cfut_ inference tokens can't read CF's GraphQL neuron analytics
// ("not authorized"), so we estimate: neurons = tokens * per-model rate.
// Rates are "neurons per 1M tokens" from CF's pricing page (verified 2026-07-06):
// https://developers.cloudflare.com/workers-ai/platform/pricing/
//
// This is an ESTIMATE (±few %), not CF billing. Good enough for "left today"
// and proactive skip. Models CF hasn't published (kimi, glm, qwq) fall back
// to a 70b-class rate — deliberately high so we skip early rather than overrun.

export const NEURON_FREE_DAILY = 10000;

// neurons per 1,000,000 tokens
export const RATES = {
  "@cf/meta/llama-3.2-1b-instruct": { in: 2457, out: 18252 },
  "@cf/meta/llama-3.2-3b-instruct": { in: 4625, out: 30475 },
  "@cf/meta/llama-3.1-8b-instruct-fp8-fast": { in: 4119, out: 34868 },
  "@cf/meta/llama-3.1-8b-instruct-awq": { in: 4119, out: 34868 }, // ~fp8-fast fallback
  "@cf/meta/llama-3.2-11b-vision-instruct": { in: 4410, out: 61493 },
  "@cf/meta/llama-3.1-70b-instruct-fp8-fast": { in: 26668, out: 204805 },
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast": { in: 26668, out: 204805 },
  "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b": { in: 45170, out: 443756 },
  "@cf/mistral/mistral-7b-instruct-v0.1": { in: 10000, out: 17300 },
  "@cf/mistralai/mistral-small-3.1-24b-instruct": { in: 31876, out: 50488 },
  "@cf/qwen/qwen2.5-coder-32b-instruct": { in: 60000, out: 90909 },
};

// Used for any model not in RATES (kimi-k2.x, glm-4.7-flash, qwq-32b, ...).
export const DEFAULT_RATE = { in: 26668, out: 204805 }; // 70b-class

const warned = new Set();

/**
 * Estimate neurons consumed by one request.
 * @param {string} model
 * @param {number} promptTokens
 * @param {number} completionTokens
 * @param {(msg: string) => void} [onFallback] called once per unknown model
 * @returns {number} estimated neurons (float)
 */
export function estimate(model, promptTokens = 0, completionTokens = 0, onFallback) {
  let rate = RATES[model];
  if (!rate) {
    rate = DEFAULT_RATE;
    if (onFallback && !warned.has(model)) {
      warned.add(model);
      onFallback(`neuron rate for "${model}" not in table — using 70b-class fallback`);
    }
  }
  return (promptTokens / 1e6) * rate.in + (completionTokens / 1e6) * rate.out;
}

/** Current UTC date as YYYY-MM-DD (the neuron day boundary — resets 00:00 UTC). */
export function todayUTC() {
  return new Date().toISOString().slice(0, 10);
}

// --- self-check: `node lib/neurons.js --selftest` ---
if (process.argv[1] && process.argv[1].endsWith("neurons.js") && process.argv.includes("--selftest")) {
  const assert = (cond, msg) => {
    if (!cond) { console.error("FAIL:", msg); process.exit(1); }
  };
  // 1M in + 1M out of llama-3.2-1b == exactly its in+out rate
  const n = estimate("@cf/meta/llama-3.2-1b-instruct", 1e6, 1e6);
  assert(Math.abs(n - (2457 + 18252)) < 1e-6, `1b 1M+1M expected 20709, got ${n}`);
  // unknown model → default rate + fallback fires exactly once
  let fires = 0;
  estimate("@cf/unknown/model-x", 1e6, 0, () => fires++);
  estimate("@cf/unknown/model-x", 1e6, 0, () => fires++);
  assert(fires === 1, `fallback should fire once, fired ${fires}`);
  const un = estimate("@cf/unknown/model-x", 1e6, 0);
  assert(Math.abs(un - DEFAULT_RATE.in) < 1e-6, `unknown in-rate expected ${DEFAULT_RATE.in}, got ${un}`);
  // zero tokens → zero neurons
  assert(estimate("@cf/meta/llama-3.2-1b-instruct", 0, 0) === 0, "zero tokens must be zero");
  // date format
  assert(/^\d{4}-\d{2}-\d{2}$/.test(todayUTC()), "todayUTC format");
  console.log("neurons.js selftest OK");
}
