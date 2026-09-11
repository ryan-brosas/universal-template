<!-- capsule-v2 -->
# Query config/deps split — how is a 1,700-line generator kept testable without spies?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which turn-loop inputs are snapshotted immutable, which stay live, and how are I/O dependencies swapped for fakes?

## QueryConfig + QueryDeps
**Path/Symbol:** `src/query/config.ts` (whole file :1-46), `src/query/deps.ts` (whole file :1-40), `src/query/transitions.ts` (whole file, 2L: `export type Terminal = any; export type Continue = any`).
**Signature:** `buildQueryConfig(): QueryConfig` where `gates = { streamingToolExecution (statsig tengu_streaming_tool_execution2), emitToolUseSummaries (env CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES), isAnt (env USER_TYPE), fastModeEnabled (env, inverted) }`; `productionDeps(): QueryDeps = { callModel, microcompact, autocompact, uuid }`.
**Data Shape:** deps override arrives via `params.deps ?? productionDeps()` (query.ts :263).

### Decisive source
```ts
// Immutable values snapshotted once at query() entry. Separating these from
// the per-iteration State struct and the mutable ToolUseContext makes future
// step() extraction tractable — a pure reducer can take (state, event, config)
// where config is plain data.
//
// Intentionally excludes feature() gates — those are tree-shaking boundaries
// and must stay inline at the guarded blocks for dead-code elimination.
```
```ts
// Passing a `deps` override into QueryParams lets tests inject fakes directly
// instead of spyOn-per-module — the most common mocks (callModel, autocompact)
// are each spied in 6-8 test files today with module-import-and-spy boilerplate.
// Scope is intentionally narrow (4 deps) to prove the pattern.
```

**Flow:** entry snapshots env/statsig gates ONCE (CACHED_MAY_BE_STALE admits staleness within one query call) → loop reads `config.gates.*` for executor/summary/fast-mode/dump-prompts decisions → tests construct `query({..., deps: {callModel: fake, ...}})` with zero module spying. fastMode gate is deliberately INLINED into config.ts ("to avoid pulling its heavy module graph … changes init order and breaks unrelated tests") rather than imported from fastMode.ts.
**Invariant:** (1) three-tier split is the contract: `feature()` = compile-time inline-only; `config.gates` = per-turn immutable snapshot; State = cross-iteration mutable; ToolUseContext = ambient mutable; (2) deps use `typeof fn` types so fake signatures can't drift from real ones; (3) scope stays NARROW on purpose — every added dep widens the fake-construction burden.
**Probe:** coverage caveat (no upstream tests for these two files). Deterministic probes: `grep -n "feature()" src/query/config.ts` → only the explanatory comment (no violations); `cat src/query/transitions.ts` shows the deliberate any-typed placeholder pending the step() extraction.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "buildQueryConfig productionDeps", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-tier input classification and typeof-keyed deps injection; adapt gate names; omit transitions.ts placeholders. Porting trap: moving a feature() check into the snapshot silently breaks dead-code elimination in external builds; snapshotting a genuinely live value (permission mode) freezes stale permissions for the whole turn.
