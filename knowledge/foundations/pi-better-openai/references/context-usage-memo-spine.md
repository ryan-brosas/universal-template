<!-- capsule-v2 -->
# Leaf-keyed memo spine — how do you cache expensive host-store reads (context usage, session name) inside a long-lived extension without serving stale values?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What exact cache key and invalidation discipline keeps a memo over a MUTABLE host API correct when events fire between renders?

## Memo families keyed by leaf identity
**Path/Symbol:** `index.ts:contextUsage` (:258-268), `sessionName` (:270-278), `invalidateContextUsage` (:251-256), `invalidateSessionName` (:280-284); cache slots declared :185-191; invalidation hooks :1222-1324.
**Signature:** `function contextUsage(ctx): ReturnType<ExtensionContext["getContextUsage"]> | undefined`; `function sessionName(ctx): string | undefined`.
**Data Shape:** Two independent memo families. Usage family = `{contextUsageCached: boolean, cachedContextUsage, cachedContextLeafId: string|null|undefined, cachedContextModel}`; session-name family = `{sessionNameCached, cachedSessionName, cachedSessionNameLeafId}`. Cache key is `(leafId, model)` for usage but `(leafId)` alone for the name — the name does not depend on the model.

### Decisive source
```ts
function contextUsage(ctx: ExtensionContext) {
  const leafId = ctx.sessionManager.getLeafId();
  const model = ctx.model;
  // hit ONLY when flag set AND every key component matches
  if (!contextUsageCached || leafId !== cachedContextLeafId || model !== cachedContextModel) {
    cachedContextUsage = ctx.getContextUsage();
    contextUsageCached = true;
    cachedContextLeafId = leafId;
    cachedContextModel = model;
  }
  return cachedContextUsage;
}

function invalidateContextUsage(): void {
  contextUsageCached = false;
  cachedContextUsage = undefined;
  cachedContextLeafId = undefined;   // key cleared WITH the flag — family stays self-consistent
  cachedContextModel = undefined;
}
```

**Flow:** (1) render-time reads go through the memo, never straight to `ctx.getContextUsage()`; (2) any event that can change the underlying store calls the invalidate fn FIRST (see event-matrix capsule); (3) next read recomputes once and re-stamps flag + all key components; (4) the two families are invalidated independently — never lumped together.

**Invariant:** A memo over a mutable host store is correct only if (a) its key includes EVERY input that affects the output — usage percent depends on BOTH conversation leaf AND current model (window size/tokenizer), so `model` is part of the key; (b) invalidation clears the flag and ALL key slots together so a partially-stale family cannot survive; (c) events that mutate content WITHOUT changing leafId (streaming deltas within one turn: `message_start/update/end`) must also invalidate — key equality alone is NOT freshness. The porter failure modes: keying by nothing ("cache per render loop") breaks multi-render turns, and keying by leafId only serves wrong percentages after `model_select`.

**Probe:** `tests/footer.test.ts:197` "reuses context usage between renders and invalidates it on message changes" — two `footer.render(100)` calls → exactly ONE `getContextUsage` call; after emitting `message_update` (same leaf) the next render recomputes (call 2); after `getLeafId` flips to `"leaf-2"` another render recomputes (call 3) and `getSessionName` is called a 2nd time. Coverage caveat: none — test file exists on disk at pin; graph indexes production code only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "contextUsage invalidateContextUsage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the leaf+model composite key, the flag+key atomic invalidation, and per-family independent lifecycle for ANY extension caching host reads across event ticks. Adapt key components to your host's identity handles (turn id, model id). Omit the specific pi `ExtensionContext` accessors.
