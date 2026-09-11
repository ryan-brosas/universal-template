<!-- capsule-v2 -->
# Click id pre-generation + async click tracking — why is the click UUID minted before the redirect while the row is written later?

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How can the redirect carry a click id on the destination URL when the click_events row does not exist yet?

## Pre-generated UUID decouples redirect latency from click persistence
**Path/Symbol:** `src/routes/redirect.ts:handleRedirect` (:339-342 mint, :344-536 setImmediate writer) vs `src/routes/sdk.ts:handleResolve` (:574-604 RETURNING-id variant).
**Signature:** `const clickId = randomUUID();` then `setImmediate(async () => { /* INSERT click_events (id, ...) VALUES ($1, ...) */ })`.
**Data Shape:** Redirect path inserts WITH the pre-generated id (19 columns incl. geo/device/utm/is_bot/bot_reason); SDK resolve path inserts WITHOUT id and reads `RETURNING id` because nothing needs the id synchronously there.

### Decisive source
```ts
// redirect.ts:339-345
// Generate the click id up front (rather than letting the DB default it on
// insert) so the synchronous redirect below can carry it on the destination
// URL while the click row is still written asynchronously with the same id.
const clickId = randomUUID();

// Track click asynchronously
setImmediate(async () => { try { ... await db.query(`INSERT INTO click_events (id, link_id, ...) VALUES ($1, $2, ...)`, [clickId, link.id, ...]);
```

**Flow:** mint uuid → build finalUrl (opt-in `append_click_id === true` appends `lf_click=<clickId>` to HTTPS destinations only, :626-634) → `reply.redirect(302)` returns immediately → setImmediate callback re-derives device/geo/bot from request headers, inserts click row, stores device fingerprint under the SAME id, emits real-time event, fires click webhooks; any failure inside is caught-and-logged (:533-535) so tracking can never break a redirect.
**Invariant:** The id on the destination URL and the id of the eventually-written row MUST be identical (correlation contract); the async writer must never throw into the request; `append_click_id` defaults OFF and skips non-parseable URLs and scheme URLs.
**Probe:** `bash -c "grep -cF 'Generate the click id up front' src/routes/redirect.ts"` → 1 (:339); direct tests: none pin this seam directly — behavior is pinned by `lf_click` append test coverage in `src/routes/redirect.test.ts` (append_click_id cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "clickId randomUUID setImmediate click_events insert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-generated correlation ids + fire-and-forget persistence with catch-log isolation for hot redirect paths; adapt storage columns; omit lf_click naming if your downstream tools differ — but keep the opt-in-default-off posture.
