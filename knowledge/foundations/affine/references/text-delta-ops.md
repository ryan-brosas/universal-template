<!-- capsule-v2 -->
# Text wrapper — delta-based rich text ops with CRLF normalization and split's delete-the-tail contract

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** What are the exact semantics of insert/format/split/join on the shared Text abstraction, and which bounds checks must a port reproduce?

## Text class
**Path/Symbol:** `blocksuite/framework/store/src/reactive/text/text.ts`: constructor (:55-94), `split` (:403-452), `join` (:259-269), `_transact` (:96-107).
**Signature:** `insert(content: string, index: number, attributes?)`; `format(index, length, format)`; `split(index, length = 0): Text` (returns RIGHT part); `join(other: Text)`.
**Data Shape:** wraps a Y.Text; exposes `deltas$: Signal<DeltaOperation[]>` and `length$` updated in one observer; all mutations go through `_transact` with origin `doc.clientID` (local marker).

### Decisive source
```ts
// split: [index, index+length) is deleted; right side starts AFTER the hole
let tmpIndex = 0;
const rightDeltas: DeltaInsert[] = [];
for (const { insert, attributes } of deltas) {
  if (typeof insert !== 'string')
    throw new BlockSuiteError(..., 'This text cannot be split because it contains non-string insert.');
  if (tmpIndex + insert.length >= index + length) {
    rightDeltas.push({ insert: insert.slice(index + length - tmpIndex), attributes });
    rightDeltas.push(...deltas.slice(i + 1));
    break;
  }
  tmpIndex += insert.length;
}
this.delete(index, this.length - index);      // deletes from index to END
const rightYText = new Y.Text();
rightYText.applyDelta(rightDeltas);
```
```ts
// join: other's delta replayed after retain-to-end — preserves OTHER's formatting
const delta = yOther.toDelta();
delta.unshift({ retain: this._yText.length });
this._yText.applyDelta(delta);
// constructor: CRLF normalized to LF for string AND delta inputs
input.replaceAll('\r\n', '\n')
```

**Flow:** every op validates bounds first (`index<0 || length<0 || index+length > yText.length ⇒ throw`) then transacts. Split computes the right-side deltas BEFORE mutating, deletes the tail `[index, end)`, and returns a NEW detached Text built from those deltas (not bound to any doc until inserted). Observer refreshes both signals on every event regardless of origin.

**Invariant:** (1) Split DELETES the covered range and everything after it — callers wanting "cut at caret" pass `length=0`; passing the selection length consumes it. (2) Split throws on embedded non-string inserts (embeds) rather than silently dropping them. (3) `join` preserves the OTHER text's attributes via delta replay; naive string concat loses bold/links. (4) Length/deltas signals are refreshed even for remote updates, so UI bound to `deltas$` needs no separate subscription.

**Probe:** upstream doc-comment example pins three split cases (`abc|de|fghi → left abc / right f,ghi`) at text.ts :388-401; bounds behavior pinned by source :162-180/:404-414 throw paths (`grep -c "out of range" text.ts` ≥ 4). No dedicated text.unit.spec.ts in-tree — consumer-tested caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "Text split join format sliceToDelta applyDelta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delta-preserving join + delete-tail split semantics verbatim; adapt signal layer; omit CRLF normalization only if the host guarantees LF input.
