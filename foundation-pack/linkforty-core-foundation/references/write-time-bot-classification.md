<!-- capsule-v2 -->
# Write-time bot classification — edge > method > ua authority ladder persisted on the click row

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** Why classify bots at ingestion instead of re-detecting at analytics time, and who is allowed to assert "this is a bot"?

## classifyBot authority order + opt-in edge header
**Path/Symbol:** `src/lib/bot-detection.ts:classifyBot` (:29-38), `edgeBotSignal` (:46-51).
**Signature:** `function classifyBot(userAgent: string | undefined, method: string | undefined, edgeIsBot?: boolean): { isBot: boolean; reason: 'edge' | 'method' | 'ua' | null }`.
**Data Shape:** Result persisted as `click_events.is_bot BOOLEAN NOT NULL DEFAULT false` + `bot_reason VARCHAR(16)`; legacy rows default human and age out of retention.

### Decisive source
```ts
// bot-detection.ts:34-37
if (edgeIsBot === true) return { isBot: true, reason: 'edge' };   // highest confidence
if (method && NON_HUMAN_METHODS.has(method.toUpperCase()))
  return { isBot: true, reason: 'method' };                        // HEAD/OPTIONS = probes/prefetch
if (isbot(userAgent ?? '')) return { isBot: true, reason: 'ua' };

// bot-detection.ts:47 — the trust gate:
if (process.env.TRUST_EDGE_BOT_HEADER !== 'true') return undefined;
```

**Flow:** redirect/SDK ingestion calls `classifyBot(ua, request.method, edgeBotSignal(request.headers['x-lf-bot']))` inside the async writer → row carries the flag → every analytics aggregate filters `is_bot = false` and reads the STORED flag rather than re-running detection (raw request signals unavailable at read time) → a partial index `idx_clicks_human_link_date ... WHERE is_bot = false` serves exactly that filter (database.ts :565-566).
**Invariant:** The edge signal is trusted ONLY behind an explicit env opt-in (`TRUST_EDGE_BOT_HEADER=true`) because otherwise any client marks its own clicks as bots (analytics poisoning via self-classification); classification happens once, at write time, and consumers must not diverge by re-detecting.
**Probe:** `bash -c "grep -cF \"TRUST_EDGE_BOT_HEADER !== 'true'\" src/lib/bot-detection.ts"` → 1 (:47); direct tests `src/lib/bot-detection.test.ts` describe('classifyBot') incl. "honors the edge signal with highest authority", "flags HEAD/OPTIONS as non-human, case-insensitively" + describe('edgeBotSignal') "is ignored unless TRUST_EDGE_BOT_HEADER=true".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "classifyBot edge method ua bot reason", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-time classification with persisted reason enum and the three-authority ladder; adapt the ua library (isbot) and edge-header name; omit the edge tier entirely if you have no trusted proxy that strips client-supplied copies — do NOT ship it default-on.
