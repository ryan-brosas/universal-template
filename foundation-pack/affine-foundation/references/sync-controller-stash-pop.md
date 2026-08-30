<!-- capsule-v2 -->
# SyncController stash/pop — optimistic local edits that bypass the CRDT until popped

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How can UI state diverge temporarily from the shared Y.Doc (draft/preview) without forking the data model, and what breaks if stash is leaked?

## SyncController proxy set + _stashProp/_popProp
**Path/Symbol:** `blocksuite/framework/store/src/model/block/sync-controller.ts`: proxy `set` trap (:178-202), `stash/pop` (:95-105), `_observeYBlockChanges` (:38-85).
**Signature:** `stash(prop: string): void` / `pop(prop: string): void`; model exposes both as methods.
**Data Shape:** `_stashed: Set<string>`; props live in a Proxy over `{key: value, key$: Signal}`; Y side stores `prop:<name>` keys on the block's Y.Map.

### Decisive source
```ts
// set trap — stashed props NEVER reach yBlock
set: (target, p, value, receiver) => {
  if (!this._byPassProxy && typeof p === 'string' && model.keys.includes(p)) {
    if (this._stashed.has(p)) {
      setValue(target, p, value);                       // local signal only
      const result = Reflect.set(target, p, value, receiver);
      this.onChange?.(p, true);                          // reported as local change
      return result;
    }
    const yValue = native2Y(value);
    if (this.yBlock.get(`prop:${p}`) === yValue) return Reflect.set(target, p, value, receiver);
    this.yBlock.set(`prop:${p}`, yValue);                // unstaged write goes to Yjs
    ...
```
```ts
// remote update lands even while stashed — model follows REMOTE, local draft kept separately? NO:
// observe writes BOTH model.props[keyName] AND signal; a stashed prop's signal is updated by
// _popProp only. pop() copies current local value INTO yBlock:
private _popProp(prop: string) {
  const value = model.props[prop];
  this._stashed.delete(prop);
  model.props[prop] = value;   // re-triggers set trap, now unstashed -> writes to yBlock
}
```

**Flow:** `stash('count')` → subsequent `model.props.count = x` updates only the local record + signal (`count$`), fires onChange(local=true) but never touches `yBlock` → remote `prop:count` changes STILL flow into the model through `_observeYBlockChanges` → `pop('count')` deletes from `_stashed`, re-assigns the same value so the now-unstashed set-trap path pushes it into Yjs.

**Invariant:** (1) Stash is per-PROP and one level deep — while stashed there is exactly ONE local value shadowing the remote; popping overwrites the remote unconditionally (last-writer-wins, NOT a merge). (2) The `_byPassProxy` flag plus `lib0 createMutex` around signal writes prevents observer→signal→observer feedback loops; removing either creates infinite recursion on every remote update. (3) Forgetting to pop leaks divergence forever — upstream tests pin that after pop, `yBlock.get('prop:count') === 4` (local wins). (4) The identity short-circuit `this.yBlock.get(...) === yValue` only helps primitives; object values always round-trip through native2Y.

**Probe:** `blocksuite/framework/store/src/__tests__/block.unit.spec.ts` :210-253 'with stash and pop': asserts `yBlock.get('prop:count')).toBe(0)` after stashed writes (:228), pop publishes 2 (:236-238), and post-re-stash remote `yBlock.set('prop:count', 3)` flows into model (:243-244).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "SyncController stash pop _byPassProxy _stashed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prop-level stash with pop-as-overwrite; adapt naming to host draft semantics; omit the mutex layer at your peril — document the loop hazard if you do.
