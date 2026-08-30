<!-- capsule-v2 -->
# GUID object tree lifecycle — how do remote objects get created, adopted, GC-collected, and disposed?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When the server creates/destroys objects on its own initiative, how does the client keep its object graph consistent — and what should a stale object do on later use?

## Dual-indexed tree with server-driven create/adopt/dispose
**Path/Symbol:** `packages/playwright-core/src/client/channelOwner.ts:ChannelOwner` (constructor 48-66, `_adopt` 113-117, `_dispose` 129-140) + `connection.ts:_createRemoteObject` (313-323).
**Signature:** `constructor(parent: ChannelOwner | Connection, type: string, guid: string, initializer)`; `_adopt(child: ChannelOwner)`; `_dispose(reason: 'gc' | undefined)`.
**Data Shape:** every object registers in TWO maps at construction: `connection._objects` (flat, guid→owner) and `parent._objects` (tree edge); initializer is validated through a generated per-type validator before the factory runs; factories are registered per connection (`_objectFactories`, "Missing type" if absent).

### Decisive source
```ts
_dispose(reason: 'gc' | undefined) {
    // Clean up from parent and connection.
    if (this._parent)
      this._parent._objects.delete(this._guid);
    this._connection._objects.delete(this._guid);
    this._wasCollected = reason === 'gc';

    // Dispose all children.
    for (const object of [...this._objects.values()])
      object._dispose(reason);
    this._objects.clear();
}
```

**Flow:** server sends `__create__ { parentGuid, type, guid, initializer }` → client validates initializer, resolves parent (throws "Cannot find parent" if unknown), invokes the type factory which self-registers into both maps. `__adopt__ { guid }` moves an existing child between parents (old parent's map delete + new parent set + repoint). `__dispose__ { reason }` unlinks from both maps and **recurses over a snapshot copy** of children (`[...values()]`) so mutation during iteration is safe; `'gc'` additionally latches `_wasCollected`.
**Invariant:** Disposal is top-down and idempotent-by-removal (deleting from maps twice is harmless); a `'gc'`-disposed object must fail fast on subsequent calls — `sendMessageToServer` throws "The object has been collected to prevent unbounded heap growth." instead of queueing a request the server will never answer. Non-GC disposal surfaces as TargetClosedError via the closed connection instead.
**Probe:** `grep -c "_wasCollected" packages/playwright-core/src/client/connection.ts` → `2`; `grep -c "reason === 'gc'" packages/playwright-core/src/client/channelOwner.ts` → `1`; `grep -c "_objects.set(guid, this)" packages/playwright-core/src/client/channelOwner.ts` → `2`; `grep -c "Missing type" packages/playwright-core/src/client/connection.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "ChannelOwner dispose", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI form: `codebase-memory-mcp cli search_graph '{"project":"ext-playwright","query":"ChannelOwner _dispose","limit":3,"detail":"ids"}'` → `client.channelOwner.ChannelOwner._dispose ... channelOwner.ts 129-140`.)

## Verdict
Adopt dual-indexing (flat lookup + tree edges), snapshot-copy recursion during child disposal, and the collected-object fail-fast. Adapt factory registration to your DI style and error copy to your API voice. Omit `_debugScopeState()` (inspector-only) unless you build a debug surface. Direct behavior pinned by library tests exercising popup adoption/context close (`tests/library/browsercontext-page-event.spec.ts`); no unit test targets `_dispose` directly — treat the grep pins above as the byte-level contract at this commit.
