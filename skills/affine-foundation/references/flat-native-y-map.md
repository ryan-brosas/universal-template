<!-- capsule-v2 -->
# ReactiveFlatYMap — dotted-path keys over ONE Y.Map with prefix-sweep deletes and signal fanout

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How can a nested JS object live in a single flat Y.Map (no nested Y types) while keeping per-subtree granularity for writes, deletes, and undo?

## createProxy (flat) / yMapUpdater / y-event-handler
**Path/Symbol:** `blocksuite/framework/store/src/reactive/flat-native-y/proxy.ts`: `createProxyHandler` (:103-203); `y-map-updater.ts`: `yMapUpdater` (:9-61); `y-event-handler.ts`: `handleUpdateOrAdd/handleDelete` (:46-117); `utils.ts`: `keyWithPrefix/getFirstKey` (:10-13,:31-35).
**Signature:** proxy traps keyed by full dotted path (`basePath ? basePath + '.' + p : p`); Y keys are `prop:<dotted.path>`; signals exposed as `<firstKey>$`.
**Data Shape:** one flat `YMap`; values are leaf primitives/Y.Text/Boxed/Y.Array only; the mirror is a nested plain-object tree of chained proxies marked via non-enumerable prototype `[proxySymbol]`.

### Decisive source
```ts
// WRITE: object assignment expands to one yMap.set PER LEAF inside a single tagged transaction
if (isPureObject(value)) {
  const syncYMap = () => yMapUpdater({...});          // deletes old subtree keys then sets leaves
  if (!isStashed) syncYMap();
  const next = createProxy({ ...options, basePath: fullPath, base: value });
  ...
}
// DELETE: prefix sweep — every key under the path dies in the same transaction
deleteProperty: (target, p) => {
  const fullPath = basePath ? `${basePath}.${p}` : p;
  ...
  yMap.doc?.transact(() => {
    const fullKey = keyWithPrefix(fullPath);
    yMap.forEach((_, key) => { if (key.startsWith(fullKey)) yMap.delete(key); });
  }, { proxy: true });
```
```ts
// REMOTE side: rebuild intermediate mirrors from 'prop:a.b.c' and prune empty parents
const keys = keyName.split('.');
void keys.reduce((acc, key, index, arr) => {
  if (!acc[key] && index !== arr.length - 1) acc[key] = {};
  if (index === arr.length - 1) acc[key] = y2Native(value, {...});
  return acc[key];
}, proxy);
```

**Flow:** set on any depth → compute fullPath + firstKey → stashed? skip Y → object value: sweep-delete `fullPath*` keys then write each leaf (`keyWithPrefix`) in one `{proxy:true}` transaction → rebuild/patch mirror proxies down the path → update root-level `<firstKey>$` signal (shallow-copied parent objects so preact effects fire). Remote event → strip `prop:` → split on '.' → walk/create mirror path; delete additionally climbs ancestors deleting now-empty objects.

**Invariant:** (1) The prefix sweep uses plain `startsWith` — key `prop:col.c` also matches `prop:col.cc`, so path components MUST be dot-delimited exactly as written (upstream accepts this; porters adding escaping must sweep on `fullPath + '.'`). (2) Signals update only at the ROOT first-key level (`getFirstKey`), so subscribing to `col$` catches `col.c.d` changes but there is no per-leaf signal. (3) Undo granularity = transaction granularity: multi-leaf object assignments undo atomically because they share one transaction. (4) Stash check uses FIRST key only — stashing `col` freezes the whole subtree including later remote writes to `col.c`.

**Probe:** `blocksuite/framework/store/src/__tests__/yjs.unit.spec.ts` :220-278 'flat': pins `proxy.col.c.d = 200 ⇒ map.get('prop:col.c.d') === 200`, whole-object replacement clearing siblings (`col.c.e === undefined` after `proxy.col.c = {d:500}`), UndoManager round-trip (:253-263), and signal writes reaching Y (`proxy.foo$.value = 'foo2'`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "ReactiveFlatYMap createProxy yMapUpdater getYEventHandler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flat-key encoding + single-transaction subtree writes; adapt the signal layering; omit if nested Y.Map values are acceptable (then use the deep proxy instead).
