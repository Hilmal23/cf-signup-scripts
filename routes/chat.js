import { Router } from "express";
import { chatUrl, embeddingsUrl, runUrl, callNormal, openStream, pumpStream } from "../lib/cf.js";
import { resolveModel } from "../lib/models.js";
import { captureBody } from "../lib/log.js";

// CF rejects multipart content — collapse OpenAI content arrays to a string.
function flattenContent(messages) {
  for (const msg of messages) {
    if (Array.isArray(msg.content)) {
      msg.content = msg.content
        .map((p) => (typeof p === "string" ? p : p?.type === "text" ? p.text ?? "" : ""))
        .join("");
    }
  }
  return messages;
}

/**
 * Run one request across the pool, retrying on 429/network errors.
 * `buildUrl(accountId)` picks the upstream URL per attempt.
 */
async function withPool({ pool, maxRetries, res, buildUrl, body, stream, model, endpoint, log, requestLog, clientRequest }) {
  const startedAt = Date.now();
  // Capture the client's original input once (before flatten/model-resolve mutate body).
  const clientReq = clientRequest ?? captureBody(body);

  const record = (account, status, extra = {}) => {
    if (!requestLog) return;
    requestLog.record({
      endpoint,
      model,
      account_id: account?.id ?? null,
      account_name: account?.name ?? null,
      status,
      stream,
      latency_ms: Date.now() - startedAt,
      client_request: clientReq,
      provider_request: captureBody(body),
      ...extra,
    });
  };

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const account = pool.getAvailable();
    if (!account) {
      record(null, 503, { error: "No available accounts", provider_request: null });
      return res.status(503).json({ error: "No available accounts", pool: pool.stats() });
    }
    const url = buildUrl(account.account_id);

    let released = false;
    const release = () => {
      if (!released) { released = true; pool.release(account.id); }
    };
    try {
      if (stream) {
        // For streaming we commit the 200 SSE response UP FRONT (before we even
        // know the upstream status) so a heartbeat can keep the connection alive
        // during CF's slow TTFB (glm-5.2: 40-80s). Trade-off: once committed we
        // can't transparently retry on 429 — but a mid-stream retry would corrupt
        // the client stream anyway. On upstream error we emit an SSE error event
        // then end.
        res.status(200);
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("X-Accel-Buffering", "no"); // caddy/nginx: don't buffer SSE
        res.setHeader("X-CF-Proxy-Account", account.name || String(account.id));
        res.flushHeaders();

        let realDataStarted = false;
        const heartbeat = setInterval(() => {
          if (!realDataStarted && !res.writableEnded) res.write(": ping\n");
        }, 15000);

        const opened = await openStream(url, account.api_key, body);
        if (opened.status === 429) {
          clearInterval(heartbeat);
          record(account, 429, { error_code: opened.errorCode, provider_response: captureBody(opened.text) });
          pool.mark429(account.id, opened.errorCode);
          // Headers already sent as 200 — surface the error as an SSE event, then end.
          res.write(`data: {"error":"rate_limited","code":${opened.errorCode ?? 429}}\n\n`);
          res.write("data: [DONE]\n\n");
          return res.end();
        }
        if (opened.status >= 400) {
          clearInterval(heartbeat);
          log.warn?.(`Account ${account.name} stream -> ${opened.status}: ${opened.text?.slice(0, 200)}`);
          record(account, opened.status, { error: opened.text?.slice(0, 200), provider_response: captureBody(opened.text) });
          res.write(`data: {"error":"upstream_error","status":${opened.status}}\n\n`);
          res.write("data: [DONE]\n\n");
          return res.end();
        }

        const writeChunk = (chunk) => {
          if (chunk && chunk.length) realDataStarted = true;
          if (!res.write(chunk)) return new Promise((r) => res.once("drain", r));
        };
        const { usage } = await pumpStream(opened.stream, writeChunk);
        clearInterval(heartbeat);
        record(account, 200, { usage, provider_response: "[SSE stream]" });
        pool.markSuccess(account.id, model, usage);
        return res.end();
      }

      const result = await callNormal(url, account.api_key, body);
      if (result.status === 429) {
        record(account, 429, { error_code: result.errorCode, provider_response: captureBody(result.text) });
        pool.mark429(account.id, result.errorCode);
        continue;
      }
      if (result.status >= 400) {
        log.warn?.(`Account ${account.name} -> ${result.status}: ${result.text?.slice(0, 200)}`);
        record(account, result.status, { error: result.text?.slice(0, 200), provider_response: captureBody(result.text) });
        return res.status(result.status).type("application/json").send(result.text);
      }
      record(account, 200, { usage: result.usage, provider_response: captureBody(result.json) });
      pool.markSuccess(account.id, model, result.usage);
      return res.json(result.json);
    } catch (e) {
      // Mid-stream: destroy so the client sees an aborted read, not a clean EOF.
      log.warn?.(`Account ${account.name} error: ${e.message}`);
      record(account, "error", { error: e.message, provider_response: null });
      if (res.headersSent) return res.destroy(e);
      continue;
    } finally {
      release();
    }
  }
  record(null, 502, { error: "All retries failed" });
  if (res.headersSent) return res.end();
  return res.status(502).json({ error: "All retries failed", pool: pool.stats() });
}

export function openaiRouter({ pool, maxRetries, log, pick, requestLog }) {
  const router = Router();

  router.post("/chat/completions", async (req, res) => {
    const body = req.body;
    if (!body || typeof body !== "object") return res.status(400).json({ error: "Invalid JSON" });
    if (!body.model) return res.status(400).json({ error: "model required" });
    const clientRequest = captureBody(body); // before resolve/flatten mutate it
    const r = await resolveModel(body.model, pick, log.warn);
    if (r.error) return res.status(r.status).json({ error: r.error, ...(r.candidates ? { candidates: r.candidates } : {}) });
    body.model = r.id;
    if (Array.isArray(body.messages)) body.messages = flattenContent(body.messages);
    return withPool({
      pool, maxRetries, res, log, requestLog, clientRequest,
      endpoint: "chat",
      buildUrl: (id) => chatUrl(id),
      body, model: r.id, stream: body.stream === true,
    });
  });

  router.post("/embeddings", async (req, res) => {
    const body = req.body;
    if (!body || typeof body !== "object") return res.status(400).json({ error: "Invalid JSON" });
    if (!body.model) return res.status(400).json({ error: "model required" });
    const clientRequest = captureBody(body);
    const r = await resolveModel(body.model, pick, log.warn);
    if (r.error) return res.status(r.status).json({ error: r.error, ...(r.candidates ? { candidates: r.candidates } : {}) });
    body.model = r.id;
    return withPool({
      pool, maxRetries, res, log, requestLog, clientRequest,
      endpoint: "embeddings",
      buildUrl: (id) => embeddingsUrl(id),
      body, model: r.id, stream: false,
    });
  });

  return router;
}

export function runRouter({ pool, maxRetries, log, pick, requestLog }) {
  const router = Router();
  // Model ids contain slashes (@cf/meta/m2m100-1.2b) — wildcard matches the
  // whole remaining path. Short ids are resolved to full first.
  router.post("/run/*", async (req, res) => {
    const model = req.params[0];
    if (!model) return res.status(400).json({ error: "model required in path" });
    const body = req.body ?? {};
    const clientRequest = captureBody({ model, ...body }); // includes raw path model
    const r = await resolveModel(model, pick, log.warn);
    if (r.error) return res.status(r.status).json({ error: r.error, ...(r.candidates ? { candidates: r.candidates } : {}) });
    return withPool({
      pool, maxRetries, res, log, requestLog, clientRequest,
      endpoint: "run",
      buildUrl: (id) => runUrl(id, r.id),
      body, model: r.id, stream: false,
    });
  });
  return router;
}
