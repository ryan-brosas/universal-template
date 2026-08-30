<!-- capsule-v2 -->
# Browser-writable settings routes — how should optional HTTP settings surfaces fail closed with bounded bodies, strict shapes, and secret-free errors while sharing one body-reading kernel?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** beyond the three auth endpoints, how does the same registrar expose a session toggle and three preference patches so oversized, malformed, or cross-origin requests never touch state?

## Fast Mode arm + settings trio inside registerOpenAICodexAuthRoutes
**Path/Symbol:** `src/auth-routes.ts:346-484` shared kernel (`json` :346-353, `OPENAI_CODEX_FAST_MODE_BODY_LIMIT = 4_096` :355, `header` :357-361, `contentLength` :363-370, `readFastModeBody` :373-414, `fastModeSessionIdFromQuery` :416-426, `fastModeBody` :428-437, `readSettingsBody` :439-445, `imagePreferencePatch` :447-459, `responseApiPatch` :461-473, `modelCatalogPatch` :475-484); registration arms `src/auth-routes.ts:544-568` (Fast Mode) and `:569-612` (settings trio).
**Signature:** handlers over `(req: IncomingMessage, res: ServerResponse)`; patch validators `(value: Record<string, unknown>) => Partial<Preferences>` that throw on any unknown key.
**Data Shape:** Fast Mode GET answers `{ enabled: boolean }`; POST takes exactly `{ sessionId, enabled }`. Settings GET returns the live detached snapshot; POST applies an allow-listed patch and returns the updated projection. Every response uses the shared no-store JSON envelope.

### Decisive source
```ts
if (req.method !== 'GET' && req.method !== 'POST') return json(res, 405, { error: 'method not allowed' })
if (!await authorize(req, res)) return
...
const type = header(req, 'content-type')
if (type === undefined || !/^application\/json(?:\s*;|$)/iu.test(type.trim())) {
  return json(res, 415, { error: 'unsupported content type' })
}
try {
  const body = fastModeBody(await readFastModeBody(req))
  if (body === undefined) return json(res, 400, { error: 'invalid input' })
  fastMode.set(body.sessionId, body.enabled)
  return json(res, 200, { enabled: fastMode.isEnabled(body.sessionId) })
} catch (error: unknown) {
  return json(res, error instanceof RangeError ? 413 : 400, { error: error instanceof RangeError ? 'request body too large' : 'invalid input' })
}
```

**Flow:** bounded-body kernel first — declared `content-length` must be pure digits and a safe integer (`TypeError`), may not exceed 4096 (`RangeError`), then bytes are accumulated with a RUNNING total check per chunk on the async-iterable path OR validated whole on a pre-set `body` string/Uint8Array; empty bodies, non-fatal UTF-8, and non-JSON all fail as `TypeError`. The query reader accepts EXACTLY one `sessionId` value passing `isFastModeSessionId`. The patch validators reject unknown keys by name ("request contains an unknown image-tool setting"), enforce booleans / array-of-strings, and feed the live policy's updaters.
**Invariant:** two deliberate orderings coexist — the Fast Mode arm checks METHOD before origin authorization while the settings trio authorizes FIRST and only then dispatches GET/POST (source-confirmed divergence in the same file); size failures map RangeError→413 and everything else to 400; the 403 refusal body is built from the trust decision and must never echo attacker-supplied input (the spec probes a secret sessionId and asserts it is absent from the response); disabling a session deletes its registry entry rather than storing `false`.
**Probe:** `tests/fast-mode-routes.spec.ts:82-141` — default-off GET, enable/disable round-trips with `registry.size === 0` after disable, remote origin → 403 with `'secret-session'` absent from the body, PUT→405, text/plain→415, empty sessionId→400, 4097-byte body→413; `tests/auth-routes.spec.ts:142-172` — model-catalog route GET returns the snapshot, POST `{models:[...]}` reaches `updateModelCatalog` and echoes the subset.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "dsh-codex\\.src\\.auth-routes\\.(readFastModeBody|fastModeBody|imagePreferencePatch)", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared bounded-body kernel with declared-plus-streamed enforcement, exact-shape payload validators that name the rejected key, RangeError/TypeError-to-status mapping, and conditional registration of settings routes only when the policy service exists. Adapt the 4096 budget, framework registration, and which ordering (method-first vs authorize-first) your threat model prefers — but pick ONE deliberately per route family. Omit unbounded request reads or echoing request identifiers in rejection bodies. Coverage: src/auth-routes.ts no_recorded_issue + metadata_match. Cross-references: auth-route-contract (the three auth endpoints sharing this registrar), trusted-origin-gate (the authorize ladder), fast-mode-toggle-contract (the client consuming these arms), tool-policy (the snapshots/updaters behind the trio).
