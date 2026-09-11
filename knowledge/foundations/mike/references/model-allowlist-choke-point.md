<!-- capsule-v2 -->
# Model allowlist choke point — how do router-prefixed model ids get validated exactly once per request?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** Where does user-requested model selection get enforced so no route forgets, and why must the check sit INSIDE the try?

## Single resolveRequestedModel(…, "throw") inside the stream try
**Path/Symbol:** `backend/src/lib/chat/streaming.ts:390-410` (comment + `resolveRequestedModel` call); helper in `src/lib/routerModels.ts`; direct test: `src/lib/chat/__tests__/streamingModelAllowlist.test.ts` (6 cases) + `src/lib/__tests__/routerModels.test.ts`.
**Signature:** `runLLMStream(params)` resolves internally: `resolveRequestedModel(model, DEFAULT_MAIN_MODEL, userId, db, "throw")`.
**Data Shape:** router-prefixed ids ("router/model-slug") must appear in the USER'S SAVED selection; first-party provider ids bypass the selection lookup; unknown/unsaved router models throw.

### Decisive source
```ts
// This lives INSIDE the try because it touches the database. Above it, a read
// failure escaped as a bare rejection — before any error event was pushed and
// before AssistantStreamError could carry the partial turn — so the SSE client
// saw the socket end with no explanation. Inside, a blip takes the same path as
// any other mid-stream failure. "throw" (not silent fallback) because `model`
// here is what the caller asked for in THIS request.
const selectedModel = await resolveRequestedModel(model, DEFAULT_MAIN_MODEL, userId, db, "throw");
```

**Flow:** every caller (chat, project chat, Word chat, tabular) funnels through runLLMStream → resolution failure becomes an `error` event (sanitizer: only UserFacingError detail shows) + AssistantStreamError carrying the partial turn → adapter receives only the RESOLVED id.
**Invariant:** One enforcement point per request — routes never re-check. Non-members are rejected even when the user brings their own API keys for the underlying provider (:91 case "also fails for non-members when the user brings their own keys"). Selection-lookup DB failures surface through the stream's error event instead of killing the socket silently.
**Probe:** `cd backend && bunx vitest run src/lib/chat/__tests__/streamingModelAllowlist.test.ts` → 6 passed at pin; `sed -n '409p' src/lib/chat/streaming.ts` → `      "throw",` (the literal appears twice incl. the :400 comment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "resolveRequestedModel router models allowlist", limit: 10 });
```

## Verdict
Adopt single-choke-point validation with explicit-throw semantics and in-try placement; adapt your routing vocabulary; omit the specific saved-selection table.
