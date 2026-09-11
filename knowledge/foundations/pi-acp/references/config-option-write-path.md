<!-- capsule-v2 -->
# Config-option write path — how do you keep the engine, the legacy mode surface, and the client UI in sync from ONE config write?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an ACP adapter implement the generic `session/set_config_option` write endpoint (plus the legacy `session/set_mode`) so that one call validates input, writes to the engine, projects onto BOTH notification surfaces, and returns server-truth config state?

## Two entry points, two engine writes, dual-surface projection
**Path/Symbol:** `src/acp/agent.ts` — `setSessionMode` (:1600-1622), `setSessionConfigOption` (:1624-1654), `isThinkingLevel` (:1657-1659), config-id constants :84-85 (`MODEL_CONFIG_ID='model'`, `THOUGHT_LEVEL_CONFIG_ID='thought_level'`). Read side + `emitConfigOptionsUpdate` in `references/config-options-selectors.md`.
**Signature:** `async setSessionConfigOption(params: SetSessionConfigOptionRequest): Promise<SetSessionConfigOptionResponse>`; `async setSessionMode(params: SetSessionModeRequest): Promise<SetSessionModeResponse>`; both start with `const session = await this.restoreSession(params.sessionId)` (auto-restore per `references/session-to-subprocess.md`).
**Data Shape:** request `{ sessionId, configId: string, value: string }`; response `{ configOptions }` where `configOptions` is a FRESH re-read via `emitConfigOptionsUpdate` (never echoed back from the request). Thinking levels are the closed six-value set `off|minimal|low|medium|high|xhigh` (type guard `isThinkingLevel`).

### Decisive source
```ts
if (typeof params.value !== 'string') {
  throw RequestError.invalidParams(`Expected string value for config option: ${configId}`)
}
if (configId === MODEL_CONFIG_ID) {
  await setSessionModel(session.proc, params.value)
} else if (configId === THOUGHT_LEVEL_CONFIG_ID) {
  if (!isThinkingLevel(params.value)) {
    throw RequestError.invalidParams(`Unknown thinking level: ${params.value}`)
  }
  await session.proc.setThinkingLevel(params.value)
  // Legacy mode surface AND fresh config options — order is pinned by test.
  void this.conn.sessionUpdate({
    sessionId: session.sessionId,
    update: { sessionUpdate: 'current_mode_update', currentModeId: params.value }
  })
} else {
  throw RequestError.invalidParams(`Unknown config option: ${configId}`)
}
const configOptions = await emitConfigOptionsUpdate(this.conn, session.sessionId, session.proc)
return { configOptions }
```

**Flow:** restore-or-create the session → validate `value` is a string (invalidParams) → dispatch on configId: `'model'` → `setSessionModel` (first-slash provider/id split, see selectors capsule); `'thought_level'` → level guard (invalidParams on unknown) → `proc.setThinkingLevel` → fire-and-forget `current_mode_update` sessionUpdate (legacy dropdown sync); anything else → invalidParams terminal. Then `emitConfigOptionsUpdate` re-reads model+thinking state from pi and pushes `config_option_update`; the response carries those same freshly-read options so the caller resyncs from server truth. `setSessionMode` is the legacy twin: same level guard + engine write + `current_mode_update`, but NO `config_option_update` in its response path — clients migrating off modes keep working while new clients use config options.
**Invariant:** validation happens BEFORE any engine write (no partial state on bad input); the thinking-level vocabulary is a closed type-guarded set shared by read (`getThinkingState`) and write paths so the option list can never advertise a level the writer would reject; for thought_level the notification ORDER is `current_mode_update` then `config_option_update` (test-pinned deepEqual of the exact update sequence); the response's `configOptions` always comes from a post-write re-read, never from the request payload.
**Probe:** `node --import tsx --test test/unit/session-config-options.test.ts test/component/session-thinking-modes.test.ts` — "setSessionConfigOption maps model changes to pi and emits config_option_update" pins the model write + single-update response; "setSessionConfigOption maps thought level changes to pi and emits sync updates" pins the EXACT two-update sequence (current_mode_update first, config_option_update second) and `currentValue:'xhigh'`; "setSessionMode maps to pi setThinkingLevel + emits current_mode_update" pins unknown-modeId → invalidParams rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "setSessionConfigOption setSessionMode isThinkingLevel emitConfigOptionsUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the validate-before-write ladder with distinct invalidParams messages per failure class (non-string value / unknown level / unknown configId), the dual-surface projection for thinking changes (legacy mode update + generic config update, in pinned order), and the response-carries-fresh-re-read contract. Adapt the config-id names and the six-level table to your engine's actual knobs. Omit the legacy `setSessionMode` twin unless your client base still speaks the older mode protocol. Direct tests executed green at the pin.
