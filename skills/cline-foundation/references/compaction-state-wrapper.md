<!-- capsule-v2 -->
# Compaction state wrapper — projection-first prepareTurn with bounded re-compaction

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How do automatic turns stay cheap once a session has already been compacted (projection + tail, not full re-summarization every turn)?

## getState → project → compact-the-projection → save-next-state; manual /compact is the fresh path
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction.ts:643-710` (`createCompactionStateAwarePrepareTurn`).
**Signature:** `({compact?, getState?, saveState?}) → ContextPipelinePrepareTurn`; `saveState(state, sourceMessages)` receives the EXACT canonical messages the hash was computed over.
**Data Shape:** Wraps any inner prepareTurn (the strategy-dispatching `createContextCompactionPrepareTurn`); returns `{messages, systemPrompt?}` where systemPrompt falls back to the persisted state's when the inner result has none.

### Decisive source
```ts
if (existingState && projectedMessages) {
    // Re-compaction intentionally starts from the compacted projection plus
    // canonical tail. This keeps automatic turns bounded without rebuilding a
    // full-transcript summary every turn; manual `/compact` is the path for a
    // fresh summary from canonical history.
    const result = input.compact
        ? await input.compact({ ...context, messages: projectedMessages, apiMessages: projectedMessages })
        : undefined;
```

**Flow:** existing state + successful projection ⇒ run the inner compaction over [compacted-view+tail] (cheap: summary rides along) ⇒ on success persist next state hashed over the FULL canonical messages and return with resolved systemPrompt ⇒ on inner decline return the projection as-is (still better than raw history). No state or failed projection ⇒ pass canonical context through untouched and persist on success.
**Invariant:** The doc comment on `saveState` is a contract: hosts must validate projections against the passed `sourceMessages`, not a separately derived transcript — mid-turn derivations can legally differ and would spuriously reject writes. Projection failures are NORMAL (tail rewrite, branch switch) and simply trigger one fresh compaction.
**Probe:** `grep -cF 'createCompactionStateAwarePrepareTurn' sdk/packages/core/src/extensions/context/compaction.ts` → 1 (export) ; upstream test "re-compacts a projection that starts with a compaction summary" exercises the loop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "createCompactionStateAwarePrepareTurn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the projection-first wrapper shape (it composes with ANY strategy); adapt persistence to host session store; omit nothing — the whole seam is ~70 lines. Runner blocked honestly; battery greps green.
