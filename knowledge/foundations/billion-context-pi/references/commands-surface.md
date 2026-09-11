<!-- capsule-v2 -->
# Command surface & dual-scale status panel — how do slash commands expose read-only introspection without mutating compression state, and how must a status panel keep two token scales apart?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How should an extension register user commands over its runtime, and what arithmetic keeps a usage panel from mixing the host's provider-scale number with your own estimate?

## Five thin commands -> one shared status report; panel renders two scales that are NEVER subtracted across

**Path/Symbol:** `src/commands.ts`: `makeCommands` (:28-113), `cacheUsageSamples` (:14-26), `statusReport` (:115-163). Direct test: `tests/commands-kit-panel.test.ts` (whole file).
**Signature:** `makeCommands(runtime: AcpRuntime) -> Array<{name, options: {description, handler(args, ctx)}}>`; `statusReport(runtime, ctx) -> Promise<string>`.
**Data Shape:** command names `acp` / `acp-status` / `acp-decompress` / `acp-search` / `acp-subagents`; panel inputs: `tokenCount` (host footer scale), `systemPromptTokens` (measured), `state`+`nudge` from a REAL `processTurn`, `unprunedTokens` (chars/4 estimate of the full projection), `cacheUsages` (per-request `{input, cacheRead, cacheWrite}`).

### Decisive source
```ts
// :122-135 — nudge arbitration on the SENT-VIEW scale; the host's
// getContextUsage is only trusted when provider-reported (>0); its tree-sum
// fallback is "the same class of false emergency" and stays log-only:
const sessionTokens = realUsage?.tokens && realUsage.tokens > 0
  ? realUsage.tokens
  : defaultCountTokens(coreMessages.map((m) => m.text ?? "").join("\n"));
const sentTokens = estimateTokens(coreMessages, coveredIds) + systemPromptTokens;
const turn = runtime.core.processTurn({ messages: coreMessages, state, config,
  tokenCount: calibrateTokens(sentTokens, runtime.density.densityFor(modelId)) });
// :139-141 — unprunedTokens is the chars/4 estimate of the SAME projection,
// so the kit derives Session-only as estimate − estimate (omp issue #18),
// never hostScale − estimate cross-scale.
```

**Flow:** `makeCommands` returns five handlers. `acp` and `acp-status` both render `statusReport` — which runs the PRODUCTION transform (`runtime.core.processTurn`) on calibrated sent-view tokens so the panel matches what the model receives (extends the status-parity contract to the human-facing panel). `acp-decompress` (:45-67) is strictly display-only: parse block id → find in `state.blocks` → `collectBlockContent(..., { full: false })` → notify text; it never flips `block.active`, so viewing never changes visibility truth. `acp-search` (:69-88) reuses the same covered-only corpus (`runtime.core.search`) and renders `[b3] (t2) topic` lines. `acp-subagents` (:90-111) is the ONLY state-mutating command: one-time setup delegating to `ensureSubagentAcpTools(undefined, installDir ? { installDir } : undefined)` with three-way outcome narration (`updated`/`skipped`/`failed`). `cacheUsageSamples` (:17-26) walks session entries and collects ONLY assistant messages carrying provider-reported `usage`; requests without cache reporting stay out of the average.
**Invariant:** (1) Read-only commands go through `runtime.stateFor(ctx)` under the same per-session mutex as the transform — they observe, never mutate. (2) The panel shows BOTH scales labelled ("Context (session accounting, host footer scale)" vs "Sent to LLM (after compression, est.)") but never subtracts one from the other; the direct test asserts `/406k/` (430k−24k) does NOT appear and Session-only reads estimate-minus-estimate (86k = 110k est − 24k est, omp issue #18). (3) Nudge arbitration uses the calibrated sent view even inside the panel, because the host's tree-sum fallback reports false emergencies (180K window vs 366K tree → EMERGENCY at 204% while chatting continues). (4) Cache-rate math excludes no-signal requests from BOTH numerator and denominator; section omitted entirely when zero usable samples. (5) Delegate usage is reported in a separate footer block, explicitly excluded from main totals.
**Probe:** EXECUTED this pass via repo runner `npm test` (node --import tsx --test): 414/414 GREEN at pin 6a88c556, including `tests/commands-kit-panel.test.ts`: host-vs-sent scale separation + no `/406k/` cross-scale subtraction (:34-56), Session-only positive derivation on the estimation scale (:58-81), prompt-cache rate 93.0% session / 90.0% last with exclusion of the cache-less request (:83-112), section omitted without usage (:114-135).
**Coverage:** check_index_coverage on src/commands.ts + tests/commands-kit-panel.test.ts → no_recorded_issue, metadata_match (generation 2026-08-25T07:58:00Z).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "makeCommands statusReport cacheUsageSamples buildStatusPanel", limit: 10, fields: ["signature", "name", "file"] });
```
EXECUTED: resolves `src.commands.makeCommands` :28-113, `src.commands.statusReport` :115-163, `src.commands.cacheUsageSamples` :17-26, plus `tests.commands-kit-panel.test.*`.

## Verdict
Adopt: one factory returning name+options pairs; read-only introspection through the production transform for parity; strict two-scale labelling with estimate-minus-estimate derivations; provider-reported-only cache averaging with omission-on-empty; separate delegate-usage accounting. Adapt command names, ctx surface, and panel rendering to your host. Omit the specific kit (`acp-kernel/panel`) internals.
