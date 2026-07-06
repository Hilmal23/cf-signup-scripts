// OpenAI-compatible chat completions. Parity with the Python handler:
// flatten content arrays, round-robin accounts, retry <= MAX_RETRIES,
// 429 -> cooldown. Adds neuron accounting via pool.markSuccess.

import { Router } from "express";
import { chatUrl, callNormal, callStream } from "../lib/cf.js";

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

export function chatRouter({ pool, maxRetries, log }) {
  const router = Router();

  router.post("/chat/completions", async (req, res) => {
    const body = req.body;
    if (!body || typeof body !== "object") {
      return res.status(400).json({ error: "Invalid JSON" });
    }
    const model = body.model;
    if (!model) return res.status(400).json({ error: "model required" });

    if (Array.isArray(body.messages)) body.messages = flattenContent(body.messages);
    const stream = body.stream === true;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const account = pool.getAvailable();
      if (!account) {
        return res.status(503).json({ error: "No available accounts", pool: pool.stats() });
      }
      const url = chatUrl(account.account_id);

      // getAvailable() reserved provisional budget on this account; release it
      // exactly once when this attempt settles, whatever the outcome.
      let released = false;
      const release = () => {
        if (!released) { released = true; pool.release(account.id); }
      };
      try {
        if (stream) {
          let prepared = false;
          const result = await callStream(url, account.api_key, body, (chunk) => {
            if (!prepared) {
              res.status(200);
              res.setHeader("Content-Type", "text/event-stream");
              res.setHeader("Cache-Control", "no-cache");
              res.setHeader("X-CF-Proxy-Account", account.name || String(account.id));
              prepared = true;
            }
            // Honor backpressure: if the client is slow, wait for drain before
            // pulling the next upstream chunk (else we buffer the whole stream).
            if (!res.write(chunk)) {
              return new Promise((resolve) => res.once("drain", resolve));
            }
          });

          if (result.status === 429) {
            pool.mark429(account.id);
            continue; // nothing written yet on 4xx path
          }
          if (result.status >= 400) {
            log.warn?.(`Account ${account.name} stream -> ${result.status}: ${result.text?.slice(0, 200)}`);
            return res.status(result.status).type("application/json").send(result.text);
          }
          pool.markSuccess(account.id, model, result.usage);
          return res.end();
        }

        const result = await callNormal(url, account.api_key, body);
        if (result.status === 429) {
          pool.mark429(account.id);
          continue;
        }
        if (result.status >= 400) {
          log.warn?.(`Account ${account.name} -> ${result.status}: ${result.text?.slice(0, 200)}`);
          return res.status(result.status).type("application/json").send(result.text);
        }
        pool.markSuccess(account.id, model, result.usage);
        return res.json(result.json);
      } catch (e) {
        // Timeout / network / abort. If we already streamed bytes we can't
        // cleanly retry — DESTROY the socket (not res.end()) so the client sees
        // an aborted read, not a clean EOF that looks like a complete response.
        log.warn?.(`Account ${account.name} error: ${e.message}`);
        if (res.headersSent) return res.destroy(e);
        continue;
      } finally {
        release();
      }
    }

    if (res.headersSent) return res.end();
    return res.status(502).json({ error: "All retries failed", pool: pool.stats() });
  });

  return router;
}
