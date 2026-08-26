<!-- capsule-v2 -->
# Session patch & usage accounting — how do session updates stay event-sourced, and how do token counts become cost?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How are all session mutations funneled into one patch primitive with tri-state field semantics, and what does correct cross-provider usage→cost math look like?

## Patch funnel + getUsage
**Path/Symbol:** `packages/opencode/src/session/session.ts` (`patch`, :736-749; all setters route through it; `getUsage`, :338-407).
**Signature:** `patch(sessionID, info: Patch)` where Patch excludes wholesale `time/share/summary/revert/permission` and re-types them as partial-or-null; `getUsage({model, usage, metadata}) → {cost, tokens}`.
**Data Shape:** Sessions live in SQLite (`SessionTable`) but mutation flows through published events (`SessionV1.Event.Updated`), so persistence is a projection of the event stream. Usage carries per-provider cache-write fallbacks in `metadata` (anthropic / vertex / bedrock / venice).

### Decisive source
```ts
// session.ts:736-748 — null means "clear", undefined means "leave alone"
const next = {
  ...current, ...info,
  time: info.time ? { ...current.time, ...info.time } : current.time,
  share:     info.share     === null ? undefined : (info.share     ? { ...current.share, ...info.share }     : current.share),
  summary:   info.summary   === null ? undefined : (info.summary   ?? current.summary),
  revert:    info.revert    === null ? undefined : (info.revert    ?? current.revert),
  permission: info.permission === null ? undefined : (info.permission ?? current.permission),
} as Info
yield* events.publish(SessionV1.Event.Updated, { sessionID, info: next })
```

```ts
// session.ts:363-366 — AI SDK v6 already includes cached tokens in inputTokens
// Always subtract cache tokens to get the non-cached input count for separate cost calculation.
const adjustedInputTokens = safe(inputTokens - cacheReadInputTokens - cacheWriteInputTokens)
```

**Flow:** every setter (`touch`, `setTitle`, `setArchived`, `setMetadata`, `setAgentModel`, `setPermission`, `setRevert`, `clearRevert`, `setSummary`, `setShare`, `setWorkspace`) calls `patch` which reads current, merges, publishes — no setter writes SQL directly. Cost path: safe() clamps non-finite/negative to 0 → subtract cache tokens from input → output minus reasoning → tiered pricing by CONTEXT size (largest matching context tier wins) → Decimal accumulation; Copilot's `totalNanoAiu` metadata short-circuits to authoritative cost when present. PASS-5 DRIFT NOTE (@0352100, session.ts :339-340/:394-398): costInfo fields are now ALSO finite-clamped (`finite(costInfo?.input ?? 0)` etc.) before the Decimal multiply — malformed model costs from models.dev (NaN/Infinity PRICING) previously poisoned total cost even though token counts were clamped; commit 9b0dd36 "ignore malformed model costs".
**Invariant:** The tri-state convention (`undefined`=no change, value=merge/set, `null`=clear) is load-bearing across five fields — flattening it breaks UI "reset to default" flows. Reasoning tokens are billed at the OUTPUT rate ("TODO: update models.dev…" comment makes it a deliberate contract). Legacy HTTP allowed negative archive timestamps; the schema keeps them permissive while excluding non-finite values that can't survive JSON round-trips (`ArchivedTimestamp = Schema.Finite`). `remove()` must work even without instance state and recurses children before publishing Deleted.
**Probe:** `packages/opencode/test/session/session.test.ts` (`"remove works without an instance"`, `"persists metadata and copies it on fork by default"`); pagination/cursor machinery behind `messages()`: `messages-pagination.test.ts` (`"pages backward with opaque cursors"` :148, `"returns items in chronological order within a page"` :180, `"handles exact limit boundary"` :221).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "getUsage patch Session service session.ts", limit: 8 });
```

## Verdict
Adopt the single-patch funnel + tri-state clearing semantics + cache-subtraction input-token rule. Adapt provider metadata fallbacks to whichever providers you serve, and keep Decimal (or equivalent) for cost accumulation. Omit nanoAIU handling unless porting GitHub Copilot billing.
