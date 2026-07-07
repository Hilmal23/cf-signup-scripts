// Recursively cap long string *values* and huge arrays, keeping the object
// structure intact so the result always re-serializes to VALID JSON. (The old
// approach sliced the serialized string, producing invalid JSON that the
// dashboard couldn't parse → it fell back to raw display.)
function truncateDeep(value, maxStr, depth) {
  if (depth > 12) return "…(too deep)";
  if (typeof value === "string") {
    return value.length > maxStr ? value.slice(0, maxStr) + `…(+${value.length - maxStr} chars)` : value;
  }
  if (Array.isArray(value)) {
    const CAP = 100;
    const out = value.slice(0, CAP).map((v) => truncateDeep(v, maxStr, depth + 1));
    if (value.length > CAP) out.push(`…(+${value.length - CAP} more items)`);
    return out;
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const k of Object.keys(value)) out[k] = truncateDeep(value[k], maxStr, depth + 1);
    return out;
  }
  return value;
}

/**
 * Capture a request/response body as a bounded, still-parseable JSON string.
 * Long string values are truncated in place (structure preserved) so the
 * dashboard can always JSON.parse and humanize it.
 * @param {any} obj object, or a string (JSON or plain like "[SSE stream]")
 * @param {number} maxStr max chars per individual string value
 */
export function captureBody(obj, maxStr = 4000) {
  if (obj == null) return null;
  try {
    const parsed = typeof obj === "string" ? JSON.parse(obj) : obj;
    return JSON.stringify(truncateDeep(parsed, maxStr, 0));
  } catch {
    // Not JSON (plain string like "[SSE stream]" or raw error text) — cap length.
    const s = typeof obj === "string" ? obj : String(obj);
    return s.length > maxStr ? s.slice(0, maxStr) + `…(+${s.length - maxStr} chars)` : s;
  }
}

export class RequestLog {
  constructor({ capacity = 500 } = {}) {
    this.capacity = capacity;
    this._buf = [];
    this._seq = 0;
  }

  /** Append one request record. Drops the oldest when at capacity. */
  record(entry) {
    this._seq++;
    const rec = {
      seq: this._seq,
      ts: Date.now(),
      ...entry,
    };
    this._buf.push(rec);
    if (this._buf.length > this.capacity) this._buf.shift();
    return rec;
  }

  /** All records, newest-first. */
  all() {
    return [...this._buf].reverse();
  }

  clear() {
    this._buf = [];
  }
}
