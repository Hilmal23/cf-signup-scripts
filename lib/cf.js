// Upstream Cloudflare Workers AI calls via native fetch.
// Both paths extract token `usage` so the pool can estimate neurons.
//   - non-stream: usage is a top-level field in the JSON body
//   - stream: usage rides the final SSE chunk (finish_reason:"stop"), just
//     before `data: [DONE]`. We tee bytes to the client while scanning for it.

const CF_BASE = "https://api.cloudflare.com/client/v4/accounts";

export function chatUrl(accountId) {
  return `${CF_BASE}/${accountId}/ai/v1/chat/completions`;
}

/** Scan one or more SSE text fragments for the last `usage` object. */
function scanUsage(buffer) {
  let usage = null;
  for (const line of buffer.split("\n")) {
    const s = line.trim();
    if (!s.startsWith("data:")) continue;
    const payload = s.slice(5).trim();
    if (payload === "[DONE]" || !payload.startsWith("{")) continue;
    try {
      const obj = JSON.parse(payload);
      if (obj.usage) usage = obj.usage;
    } catch {
      /* partial chunk; ignore */
    }
  }
  return usage;
}

/**
 * Non-streaming completion.
 * @returns {{status:number, headers:Headers, json?:any, text?:string, usage?:any}}
 */
export async function callNormal(url, apiKey, body, { timeoutMs = 120000 } = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const status = res.status;
  if (status >= 400) {
    return { status, headers: res.headers, text: await res.text() };
  }
  const json = await res.json();
  return { status, headers: res.headers, json, usage: json.usage ?? null };
}

/**
 * Streaming completion. Pipes chunks to `write(chunk)` as they arrive and
 * resolves with the parsed usage once the upstream stream ends.
 * @param {(chunk: Uint8Array) => Promise<void>|void} write
 * @returns {{status:number, headers:Headers, text?:string, usage?:any}}
 *   On upstream error (status >= 400) returns {status, text} and writes nothing.
 */
export async function callStream(url, apiKey, body, write, { timeoutMs = 300000 } = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (res.status >= 400) {
    return { status: res.status, headers: res.headers, text: await res.text() };
  }

  const decoder = new TextDecoder();
  let tail = ""; // carry incomplete trailing line across chunks for usage scan
  let usage = null;

  for await (const chunk of res.body) {
    await write(chunk);
    tail += decoder.decode(chunk, { stream: true });
    // Scan only complete lines; keep the remainder for the next chunk.
    const nl = tail.lastIndexOf("\n");
    if (nl >= 0) {
      const found = scanUsage(tail.slice(0, nl));
      if (found) usage = found;
      tail = tail.slice(nl + 1);
    }
  }
  const found = scanUsage(tail);
  if (found) usage = found;

  return { status: res.status, headers: res.headers, usage };
}
