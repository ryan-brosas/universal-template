<!-- capsule-v2 -->
# Status-parity reporting — how can a status view show exactly what the model will receive rather than what the raw session holds?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a status/inspect tool compute its numbers so they match the transformed context instead of the pre-transform one?

## Re-run the production transform inside the status handler; split the unclassifiable token gap honestly
**Path/Symbol:** `src/status-tool.ts`: `makeStatusTool` (:21), `handleStatus` (:47-119); `src/commands.ts`: `cacheUsageSamples` (:17-26), `makeCommands` (:28-113, five slash commands incl. `/acp` + `/acp-status` both → `statusReport`), `statusReport` (:115-163).
**Signature:** both surfaces call `runtime.core.processTurn({messages, state, config, tokenCount})` and report on `turn.messages` / `turn.nudge` / `turn.state` — never on the raw coreMessages.
**Data Shape:** the `/acp` panel is rendered by the SHARED kit (`buildStatusPanel` from `acp-kernel/panel`, commands.ts :6/:143) fed host-specific inputs: measured `systemPromptTokens`, sent-view tokenCount, `unprunedTokens` (chars/4 of the FULL projection so the kit's Session-only number sits on the same estimation scale — "never cross-scale; omp issue #18"), and per-assistant-message cache usage samples (`input/cacheRead/cacheWrite`, absent-reporting requests stay 0/0 and are excluded from averages). The `acp_status` TOOL renders through the kernel's `buildStatusReport` instead (status-tool.ts :4/:71); overview mode appends the nudge decision, kernel-formatted compressible+protected ranges (:97-103), and a delegate-usage tail with merged-mode disclosure (:104-117).
### Decisive source
```ts
// commands.ts:115-135 (current pin; anchors unchanged since pass 8) — the parity ruling EXTENDED to scale discipline:
const realUsage = ctx.getContextUsage?.();
// Nudge arbitration on the SENT-VIEW scale — must match the context
// transform and acp_status. pi's getContextUsage is anchored on the last
// assistant's provider-reported usage when available ... but falls back to
// summing the whole session tree ... same class of false emergency as the omp
// 180K-window/366K-tree report. The tree-scale number stays in the log only.
const sentTokens = estimateTokens(coreMessages, coveredIds) + systemPromptTokens;
const turn = runtime.core.processTurn({ messages: coreMessages, state, config,
  tokenCount: calibrateTokens(sentTokens, runtime.density.densityFor(modelId)) });
```
**Flow:** load state via `runtime.stateFor(ctx)` → compute the calibrated sent view EXACTLY as the context transform does (`sent-view-arbitration` capsule) → processTurn → hand `turn.state` + nudge to the shared kit panel → append pi-specific footer: delegate usage ("excluded from main totals") with in/out/cost. The tool surface mirrors this through `handleStatus`. Token-truth ladder is consistent across all surfaces: env override → adapter config → learned overflow window → output-headroom-reserved live window → 150k fallback.
**Invariant:** a status view that bypasses the production transform reports phantom content (consumed calls, pruned messages); a status view that uses a DIFFERENT token scale than the decisions reports phantom emergencies. Unattributable tokens are labeled as a residual "framework" bucket, never silently dropped from the total. Cache-hit samples must exclude no-reporting requests from AVERAGES rather than treating them as zero-hit.
**Probe:** `cd $REFERENCE_ROOT/billion-context-pi && npx tsx --test tests/commands-kit-panel.test.ts` — GREEN at pin (shared-panel rendering with host inputs; `tests/status-parity.test.ts` does not exist at this pin — the fallback path is the live one).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "statusReport buildStatusPanel cacheUsageSamples makeCommands", limit: 10 });
```

## Verdict
Adopt transform-parity AND scale-parity for any inspect/status surface: same pipeline, same calibrated sent-view arithmetic, shared renderer with host-specific measured inputs. Adapt rendering to your UI; keep the honest residual bucket. Omit the ASCII box art.
