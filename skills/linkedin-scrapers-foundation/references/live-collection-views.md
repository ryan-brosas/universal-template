<!-- capsule-v2 -->
# Live collection views — how do I expose "a set of results" as an object that queries lazily instead of materializing?

**Source:** lh-basis ISC (core/models package.json) — patterns only, dist-compiled tree; Codebase Memory `lh-basis` (models plane excluded by design → source-read probes). **Question:** How can a collection's `size`, indexing, and iteration all be LIVE queries over a data source while still satisfying JS iteration protocols?

## The lazy-view shape
**Path/Symbol:** `core/models/dist/models/collections/MessagesCollection.ts:MessagesCollection`; base `collections/VersionedCollection.ts:VersionedCollection` (get/first/last/[Symbol.asyncIterator] defaults).
**Signature:** `constructor(searchData, source)`; `get size()` → live count; `[Symbol.asyncIterator]()` → `{ next(): Promise<{done, value}> }`; `async get(i)`, `async slice(start, end)`, `async first()`, `async last()`.
**Data Shape:** `searchData` = serialized query descriptor (itself SuperJSON-transformed); every method delegates to `this.source.people.messages.*`.

### Decisive source
```ts
get size() { return this.source.people.messages.getMessagesCount(this.searchData); }
[Symbol.asyncIterator]() {
  let prevMessageSearchResult;
  return {
    next: async () => {
      const messageSearchResult =
        await this.source.people.messages.getNextMessage(this.searchData, prevMessageSearchResult?.message.id);
      if (messageSearchResult) prevMessageSearchResult = messageSearchResult;
      return { done: !messageSearchResult, value: messageSearchResult };
    },
  };
}
async get(i)  { return (await this.source.people.messages.getMessages(this.searchData, i, i + 1))[0]; }
async last()  { return (await this.source.people.messages.getMessages(this.searchData, -1))[0]; }
```

**Flow:** construction stores ONLY the query + source handle — zero rows fetched → `size` fires a COUNT each time it's read → iteration is cursor-chained (`getNextMessage(searchData, prev.id)`) so pages stay consistent as new messages arrive → random access compiles to one-row slice queries. `VersionedCollection` adds the generic convenience layer (`first() = slice(0,1)[0]`, negative-index `last()`) and composes `WithLiAccountId(SerializableWithSource)` mixin-style for per-account tenancy.
**Invariant:** NOTHING is ever materialized wholesale — a "collection" here is a query with array syntax. The iterator keeps its own `prev` cursor and only advances on success (failed fetch leaves the chain re-runnable). Python-style negative index in `last()` is delegated to the source layer. Compositional mixins (`WithLiAccountId(Base)`) carry the tenancy key without a base-class explosion.
**Probe:** no tests exist for this plane (dist-only vendor artifact) — coverage caveat recorded; pinned by whole-file source reads at HEAD + graph-exclusion verification.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "VersionedCollection MessagesCollection", limit: 5 }); // 0 hits — plane excluded by design
```

## Verdict
Adopt the lazy-view contract (array-protocol facade over paged queries) for any result-set surface over slow IO. Adapt the mixin composition to your language (Python: `__len__`/`__getitem__`/`__aiter__`). Omit the specific source-method names.
