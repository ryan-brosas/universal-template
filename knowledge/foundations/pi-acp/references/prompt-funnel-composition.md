<!-- capsule-v2 -->
# Prompt-funnel composition — in what order do restore, image gate, builtin dispatch, the usage tail, and the IDE gates run inside prompt()?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do the five stages of prompt() compose — where exactly do the image gate, the always-run usage tail, the IDE gates, and the error mapping sit relative to each other?

## PiAcpAgent.prompt — five-stage pipeline
**Path/Symbol:** `src/acp/agent.ts:prompt` (:571-1039) — restore :572, `promptToPiMessage` :574, builtin gate :578, `session.prompt` :1023, usage tail :1027, IDE-gate tail :1040-1057, error mapping :1029-1038.
**Signature:** `async prompt(params: PromptRequest): Promise<PromptResponse>` — response `{stopReason, usage?, _meta?: {piAcp: {inspection?, mutationViolations?, error?}}}`.
**Data Shape:** `usage` = cumulative session stats or `undefined` (null collapses to omitted); `_meta.piAcp` keys added ONLY when non-empty; `ideMutationsBefore` snapshot taken BEFORE `session.prompt`.

### Decisive source
```ts
const ideMutationsBefore = new Set<string>(session.mcpBridge?.appliedMutationPaths ?? [])
const result = await session.prompt(message, images)

// UNSTABLE ACP PromptResponse.usage: report cumulative session tokens after the
// turn settles (best effort; a slow or absent pi stats call omits the field).
const usage = await this.collectTurnUsage(session)

if (result === 'error') {
  if (session.wasCancelRequested()) return { stopReason: 'cancelled', usage }
  return { stopReason: 'end_turn', usage, /* …_meta.piAcp.error… */ }
}
if (result === 'end_turn') {
  const inspection = await this.enforceIdeInspection(session)
  const mutationViolations = await this.enforceIdeMutationProvenance(session, ideMutationsBefore)
  session.touchedFilePaths.clear()
  const piAcpMeta: Record<string, unknown> = {}
  if (inspection) piAcpMeta.inspection = inspection
  if (mutationViolations && mutationViolations.length > 0) piAcpMeta.mutationViolations = mutationViolations
  if (Object.keys(piAcpMeta).length > 0) return { stopReason: 'end_turn', usage, _meta: { piAcp: piAcpMeta } }
}
return { stopReason: result, usage }
```

**Flow:** (1) `restoreSession(sessionId)` — live session, in-flight dedup, or fresh spawn; (2) `promptToPiMessage` splits the prompt blocks into `{message, images}`; (3) builtin slash dispatch runs ONLY when `images.length === 0 && message.trimStart().startsWith('/')` — an image prompt starting with '/' goes to the model; (4) `session.prompt(message, images)` runs the turn; (5) the tail ALWAYS collects usage (`withTimeout(getSessionStats, 2500)` → `sessionStatsToAcpUsage`, null on slow/fail → field omitted), then on `end_turn` runs the two never-throw IDE gates, clears `touchedFilePaths`, and attaches `_meta.piAcp` only when a gate produced output. Error mapping: pi `'error'` + cancel-requested → `cancelled`; otherwise → `end_turn` + `_meta.piAcp.error` (ACP StopReason has no `error`).
**Invariant:** usage collection is unconditional on every completed turn (success AND error paths) and can never fail the turn; the mutation snapshot precedes the turn so only THIS turn's IDE applications offset violations; `touchedFilePaths.clear()` runs after the gates so stale paths never mask the next turn; the image gate sits BEFORE dispatch so slash-text-with-images is never intercepted.
**Probe:** `node --import tsx --test test/unit/agent-gaps.test.ts` (usage attachment deep-equal) + `test/unit/turn-settling` behavior via `test/unit/session-usage.test.ts` (usage matrix) + `test/component/agent-steering-followup-modes.test.ts` (dispatch stage).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "prompt collectTurnUsage enforceIdeInspection enforceIdeMutationProvenance wasCancelRequested", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stage order (restore → block-split → image-gated dispatch → turn → unconditional best-effort usage tail → never-throw gates → meta-only-when-non-empty) and the cancel-aware error mapping. Adapt the gate set and `_meta` envelope to your protocol. Omit the IDE gates entirely if your host has no lint/mutation-provenance channel — the funnel still stands. Coverage caveat: the composition itself is pinned only by the usage test + dispatch component tests; the ordering of gates vs clear is source-read.
