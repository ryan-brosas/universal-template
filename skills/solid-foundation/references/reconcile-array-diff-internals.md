<!-- capsule-v2 -->
# Reconcile array-diff internals — how does applyState reuse nodes when keys repeat, reorder, appear, and vanish?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (gen 2026-08-25T20:12:15Z). **Question:** What is the exact per-stage algorithm of `applyState`'s array branch, and where does the keyed chain matter?

## modifiers.ts applyState array stages
**Path/Symbol:** `packages/solid/store/src/modifiers.ts:applyState` (:15-133; array branch :37-122).
**Signature:** `function applyState(target: any, parent: any, property: PropertyKey, merge: boolean | undefined, key: string | null)` — recursive; top call wraps state as `{ [$ROOT]: state }`.
**Data Shape:** `previous` = live store node mutated in place via `setProperty`; `temp = new Array(target.length)` holds reused nodes whose destination index isn't known yet; `newIndices: Map<keyVal, targetIndex>` + `newIndicesNext: number[]` form a per-key linked list for DUPLICATE keys.

### Decisive source
```ts
// prepare a map of all indices in target
newIndicesNext = new Array(newEnd + 1);
for (j = newEnd; j >= start; j--) {
  item = target[j];
  keyVal = key && item ? item[key] : item;
  i = newIndices.get(keyVal);
  newIndicesNext[j] = i === undefined ? -1 : i;   // chain to next occurrence of same key
  newIndices.set(keyVal, j);
}
// step through all old items to check reuse
for (i = start; i <= end; i++) {
  item = previous[i];
  keyVal = key && item ? item[key] : item;
  j = newIndices.get(keyVal);
  if (j !== undefined && j !== -1) {
    temp[j] = previous[i];        // REUSE old node at its new index
    j = newIndicesNext[j];
    newIndices.set(keyVal, j);    // consume this link so duplicates match one-to-one
  }
}
```

**Flow:** (1) common prefix matched by reference or key equality recurses into items (:45-57) so unchanged subtrees deep-diff instead of replacing; (2) common suffix fills `temp` from the ends (:62-75); (3) fast path — if prefix consumed everything (`start > newEnd || start > end`), write remaining target items, then reinsert `temp` and recurse (:78-86); (4) otherwise build the duplicate-key chain Map backwards, sweep old items forward consuming one chain link per reuse, then write every target index — reused node from `temp` + recursion, or fresh value directly (:89-114); (5) explicit `setProperty(previous, "length", …)` truncation whenever previous ran longer (:84, :120). Non-keyed/empty-array fallback loops index-by-index (:115-119). Keyed mode only engages when BOTH arrays are non-empty and (`!merge` or first target item carries a non-null key) (:38-42).
**Invariant:** A key may appear multiple times in `target`; the `newIndicesNext` chain guarantees each old node with that key is claimed exactly once (one-to-one matching), so `Object.is(unwrap(state.users[i]), JOHN)` identity survives arbitrary reorder/append/shrink. Key mismatch on an item still replaces that subtree wholesale (applyState's entry guard :26-35). `merge: true` with `key: null` degrades to positional overwrite of every property.
**Probe:** `packages/solid/store/test/modifiers.spec.ts` "Reconcile reorder a keyed array" (:66-92) pins node identity across reorder → append → shrink via `Object.is(unwrap(state.users[i]), …)`; "Reconcile overwrite in non-keyed merge mode" (:94-120) pins `{merge:true, key:null}` positional overwrites; "Reconcile array with nulls" (:35-42) pins null-as-value identity (null is not wrappable ⇒ replaced, not diffed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "applyState reconcile produce setterTraps", limit: 10 });
```

## Verdict
Adopt the five-stage order verbatim — prefix-recursion, suffix-temp, fast path, chained duplicate-key map, explicit length truncation; it is what makes in-place store arrays DOM-stable under reorder. Adapt `keyVal` derivation if your identity field differs. Omit the merge-mode gate only if you never accept unkeyed merges.
