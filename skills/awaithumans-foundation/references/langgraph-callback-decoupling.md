<!-- capsule-v2 -->
# Framework-Agnostic LangGraph Resume Handler — how does a webhook restart a paused graph without importing the runtime?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does the callback half of a durable adapter stay decoupled from `@langchain/langgraph` while still resuming its graphs?

## Structural interfaces + injected Command + mirrored HKDF
**Path/Symbol:** `packages/typescript-sdk/src/adapters/langgraph/index.ts` — `LangGraphInvokable` (:372–380), `CommandConstructorLike` (:387–389), `createLangGraphCallbackHandler` (:449–489), `verifySignature`/`signBody`/`deriveHmacKey` (:503–558).
**Signature:** `createLangGraphCallbackHandler({graph, command, payloadKey}) -> (input: {threadId, body, signatureHeader}) -> Promise<{status, error?}>`; `signBody(body: Uint8Array, payloadKey: string): Promise<string>` (public/exported for DIY dispatchers).
**Data Shape:** resume value = FULL webhook body (`CompletionResume{task_id?, status?, response?, verification_attempt?...}`); invoke config = `{configurable: {thread_id}}`; signature header normalized to `sha256=<hex>` prefix.

### Decisive source
```ts
// Static import: the interrupt symbol IS LangGraph's resume protocol.
// We can't dynamic-import inside a node call (interrupt has to be the
// EXACT module instance the host runtime uses ...)   ← graph side only
//
// handler side — Command is INJECTED instead:
/**
 * The `Command` class from `@langchain/langgraph`. Pass it in directly
 * (`Command`) — we accept it as a parameter so the SDK itself doesn't
 * need to import the runtime symbol; that import happens inside YOUR
 * app ... which sidesteps the dual-package hazard the Temporal adapter
 * ran into.
 */
const command = new options.command({ resume: payload });
await options.graph.invoke(command, { configurable: { thread_id: input.threadId } });
```

**Flow:** verify HMAC (HKDF-SHA256 salt `awaithumans-webhook-v1` info `v1` over base64url-decoded PAYLOAD_KEY — mirrors Python server derivation; constant-time compare with early length exit) → 401 on bad sig → JSON.parse body (400 on bad) → `graph.invoke(new Command({resume}), configurable.thread_id)` → 200; any throw ⇒ 500.
**Invariant:** asymmetry by design — graph-side `interrupt()` must be a STATIC import of the exact module instance (like Temporal's CancellationScope), but handler-side `Command` must be INJECTED so the dual-package hazard never reappears. Status-code-shaped results (never thrown) let callers wire any framework. A third adapter should move shared HMAC code to `internal/webhook.ts` (in-source TODO).
**Probe:** TS suite has no langgraph-handler test file at this pin; the Python twin's resolve matrix IS tested (`packages/python/tests/adapters/test_idempotency_collision.py`:149–199, the four `test_langgraph_resolve_*` tests) and `temporal-adapter.test.ts` pins the sibling — coverage caveat recorded in-capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "createLangGraphCallbackHandler CommandConstructorLike signBody deriveHmacKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt structural-interface injection for framework classes, full-body resume values, and status-shaped handler results. Adapt the HMAC plumbing location if you have ≥3 adapters (extract to internal/webhook.ts as upstream plans). Omit nothing else — the static-vs-injected split is the load-bearing lesson.
