<!-- capsule-v2 -->
# Solid mapArray — how does <For> diff by value identity with prefix/suffix skipping and per-item roots?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** What is the exact reconciliation algorithm keyed by item (not index), and where do the index accessors update?

## mapArray: S-array diff with backward newIndices map
**Path/Symbol:** `packages/solid/src/reactive/array.ts:mapArray` (:49-177), inner closure state (:54-58) and `mapper` (:167-175).
**Signature:** `mapArray<T, U>(list: Accessor<readonly T[] | undefined | null | false>, mapFn: (v: T, i: Accessor<number>) => U, options?: { fallback?: Accessor<any> }): () => U[]`.
**Data Shape:** closure arrays `items` (last seen raw items, FALLBACK sentinel slot 0 when empty+fallback), `mapped`, `disposers`, and optional `indexes: Setter[]` — allocated ONLY when `mapFn.length > 1` (i.e. the user's map function declares the index parameter).

### Decisive source
```ts
// skip common prefix
for (start = 0, end = Math.min(len, newLen);
     start < end && items[start] === newItems[start]; start++);
// common suffix
for (end = len - 1, newEnd = newLen - 1;
     end >= start && newEnd >= start && items[end] === newItems[newEnd];
     end--, newEnd--) {
      temp[newEnd] = mapped[end];
      tempdisposers[newEnd] = disposers[end];
      indexes && (tempIndexes![newEnd] = indexes[end]);
}
// 0) prepare a map of all indices in newItems, scanning backwards so we encounter them in natural order
newIndices = new Map<T, number>();
newIndicesNext = new Array(newEnd + 1);
for (j = newEnd; j >= start; j--) {
      item = newItems[j];
      i = newIndices.get(item)!;
      newIndicesNext[j] = i === undefined ? -1 : i;
      newIndices.set(item, j);
}
```

**Flow:** re-run reads `list()` then `$TRACK`s it top-level and `untrack`s the diff → empty-list fast path disposes everything (+ optional fallback root at index 0) → fresh-list fast path creates a `createRoot(mapper)` PER ITEM → general path: skip common prefix/suffix (identity `===`) → build backwards Map of new positions with `newIndicesNext` chain for duplicate items → walk old items; found ⇒ move (temp[j] = mapped[i]); not found ⇒ dispose → fill remaining slots with NEW roots → shrink via slice.
**Invariant:** Item IDENTITY is the key — duplicated values are handled by the `newIndicesNext` linked-chain so each old occurrence maps to exactly one new occurrence. Index signals fire on MOVE (`indexes[j](j)` in step 2). Each mapped row lives in its own root so disposing one row never tears down neighbors. The `(newItems as any)[$TRACK]` read is what makes the outer memo reactive to array replacement under stores.
**Probe:** `grep -c 'skip common prefix' packages/solid/src/reactive/array.ts` → `1`; `grep -c 'common suffix'` → `1`; `grep -c 'newIndices.get(item)'` → `2`. Behavior pinned by `test/array.spec.ts` both describes (:4-54).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "mapArray newIndicesNext disposers mapper", limit: 10 });
```

## Verdict
Adopt the whole diff verbatim for keyed list reconciliation. Adapt `createRoot(mapper)` to your disposal system. Omit the fallback branch if your host handles empty states elsewhere. `<Index>` (indexArray, same file :186-254) is the MIRROR contract: stable rows keyed by position, per-row value signal updated via `signals[i](() => newItems[i])` — port as a pair.
