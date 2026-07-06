// Health, models, and dashboard admin API (accounts, stats, manual import).

import { Router } from "express";
import { importFrom9router } from "../lib/importer.js";
import { NEURON_FREE_DAILY, todayUTC } from "../lib/neurons.js";

export const MODELS = [
  "@cf/meta/llama-3.2-1b-instruct",
  "@cf/meta/llama-3.2-3b-instruct",
  "@cf/meta/llama-3.1-8b-instruct-fp8-fast",
  "@cf/meta/llama-3.1-8b-instruct-awq",
  "@cf/meta/llama-3.1-70b-instruct-fp8-fast",
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
  "@cf/mistralai/mistral-small-3.1-24b-instruct",
  "@cf/moonshotai/kimi-k2.5",
  "@cf/moonshotai/kimi-k2.6",
  "@cf/zai-org/glm-4.7-flash",
  "@cf/qwen/qwq-32b",
  "@cf/qwen/qwen2.5-coder-32b-instruct",
];

// Shape one DB row for the dashboard: expose derived neuron figures, never the key.
function shapeAccount(row) {
  const today = todayUTC();
  const usedToday = row.neurons_day === today ? row.neurons_today : 0;
  const reqsToday = row.neurons_day === today ? row.requests_today : 0;
  const now = Date.now() / 1000;
  const inCooldown = row.cooldown_until > now;
  let status = "available";
  if (!row.is_active) status = "inactive";
  else if (usedToday >= NEURON_FREE_DAILY) status = "exhausted";
  else if (inCooldown) status = "cooldown";
  return {
    id: row.id,
    name: row.name,
    account_id: row.account_id.slice(0, 8),
    is_active: !!row.is_active,
    status,
    neurons_today: Math.round(usedToday),
    neurons_remaining: Math.max(0, Math.round(NEURON_FREE_DAILY - usedToday)),
    neurons_free_daily: NEURON_FREE_DAILY,
    requests_today: reqsToday,
    cooldown_seconds: inCooldown ? Math.round(row.cooldown_until - now) : 0,
  };
}

export function adminRouter({ db, pool, ninePath, log }) {
  const router = Router();

  router.get("/health", (_req, res) => res.json({ status: "ok", pool: pool.stats() }));

  router.get("/v1/models", (_req, res) => {
    res.json({
      object: "list",
      data: MODELS.map((id) => ({ id, object: "model", owned_by: "cloudflare" })),
    });
  });

  router.get("/api/stats", (_req, res) => res.json(pool.stats()));

  // Full account list — the dashboard paginates/sorts client-side.
  router.get("/api/accounts", (_req, res) => {
    const rows = db.prepare("SELECT * FROM accounts ORDER BY id").all();
    res.json({ accounts: rows.map(shapeAccount), stats: pool.stats() });
  });

  router.post("/api/import", (_req, res) => {
    try {
      const result = importFrom9router(db, ninePath, log);
      res.json(result);
    } catch (e) {
      log.error?.(`import failed: ${e.message}`);
      res.status(500).json({ error: e.message });
    }
  });

  return router;
}
