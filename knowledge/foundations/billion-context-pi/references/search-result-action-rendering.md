<!-- capsule-v2 -->
# Search-tool result rendering — how does a context-search tool teach the model the next action instead of returning raw data?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** How should a search tool present ranked hits over compressed blocks and historical messages so the model can act on them without a follow-up question?

## makeSearchTool: ranked refs + per-result decompress commands
**Path/Symbol:** `src/search-tool.ts` (88L, whole): `makeSearchTool` (:15-39), `handleSearch` (:41-56), `formatResult` (:58-77).
**Signature:** tool `search_context({ query, limit? })` → kernel `searchBlocks(docs, query, {limit})`; docs built fresh per call by `buildSearchDocs(ctx, state)`.
**Data Shape:** each hit renders three lines — meta header (`block b3 | (role) T2 score:0.87 1.2K` + 50-char title with … ellipsis), preview text, and an ACTION line: blocks get `→ decompress({ blockId: "b3" })`, covered messages get `→ decompress({ blockId: "…" })  (block containing message m00350)`, uncovered messages read `(message m00007 is still visible in context)`.

### Decisive source
```ts
// src/search-tool.ts:70-74 — every result carries its own next command
const decompressHint = r.kind === "block"
    ? `→ decompress({ blockId: "${r.ref}" })`
    : r.blockId
      ? `→ decompress({ blockId: "${r.blockId}" })  (block containing message ${r.ref})`
      : `(message ${r.ref} is still visible in context)`;
```

**Flow:** resolve runtime state under the session mutex → build the corpus fresh (covered-only blocks + historical messages, per search-index capsule) → run the kernel's scored search → empty results return a census message ("No matches … across N block(s) and M historical message(s)") so the model knows what WAS searched, not just "nothing found" → hits render meta+preview+decompress-hint. Errors are logged with scope/session/query via `logThrow` then RE-THROWN (:30-35) — the host renders the failure; the log carries the forensic fields.
**Invariant:** (1) results are self-describing actions: the model never needs to guess how to retrieve full content — copy the printed command; (2) visible-in-context hits must say so explicitly or the model wastes a decompress round-trip on content it already has; (3) the empty-result census reports both corpus sizes because "no match" is only interpretable against what was searched.
**Probe:** no dedicated upstream suite exists for search-tool.ts (deterministic greps T8-T10 pin makeSearchTool wiring :15-17, the decompress-hint ternary :70-74, and the re-throw logging :32-34); the corpus side is pinned by tests/messages.test.ts + tests/decompress-cmd.test.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "makeSearchTool searchBlocks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the self-describing-result doctrine (action line per hit, visibility statement for free hits, census on empty) for any retrieval tool exposed to a model. Adapt the concrete downstream tool name and ref grammar to your own. Omit the role/tier/score header fields if your scorer lacks them — but keep size, it prices the decompress decision.
