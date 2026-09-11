<!-- capsule-v2 -->
# Collection object guards — What makes an object a valid Collection (the fourth action-payload shape)?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how does the kernel recognize a list-like domain object that is more than a plain array but less than an entity?

## Behavior-surface registry with byte-identical family guards
**Path/Symbol:** `core/public-methods/models/collections/PeopleCollection/guards.js:isIPeopleCollection` (8–12); `core/public-methods/models/collections/OrganizationsCollection/guards.js:isIOrganizationsCollection` (8–12) — the two bodies are BYTE-IDENTICAL.
**Signature:** `isIPeopleCollection(value): boolean`; `isIOrganizationsCollection(value): boolean`.
**Data Shape:** dbItem (`id>0`) ∧ properties `{versions, name}` ∧ method surface `{add, remove, clear, addWithStats, removeWithStats}`. The shared-types payload files (`shared-types/peopleCollections.js`, `organizationsCollections.js`) are empty compiled type shells — only these runtime guards survive.

### Decisive source
```js
function isIPeopleCollection(value) {
    return Boolean((0, dbItem_1.isIDBItem)(value) &&
        (0, objects_1.objectHasProperties)(value, ['versions', 'name']) &&
        (0, objects_1.objectHasMethods)(value, ['add', 'remove', 'clear', 'addWithStats', 'removeWithStats']));
}
// OrganizationsCollection/guards.js:8-12 — same body verbatim
```

**Flow:** identity (dbItem row) + version vector + display name + five mutation methods = a Collection. This is the "Collection object" accepted as the fourth shape by the action-payload validators (see polymorphic-list-payload-guards): APIs take entities, per-entity tuples, one batch tuple, OR one of these registries.
**Invariant:** unlike campaign/action/result families there is NO discrimination — the SAME object passes both people and org collection guards; membership semantics live behind the methods, not in shape. The `*WithStats` method pair implies mutations report queue-stat deltas, not just success. `objectHasMethods` requires key-presence AND `typeof === 'function'`; the whole conjunction is wrapped in explicit `Boolean(...)` here (cosmetic — operands are already boolean).
**Probe:** deterministic node-require:
```bash
node -e "const P=require('$REFERENCE_ROOT/lh-basis/core/public-methods/models/collections/PeopleCollection/guards.js');const O=require('$REFERENCE_ROOT/lh-basis/core/public-methods/models/collections/OrganizationsCollection/guards.js');const m={add(){},remove(){},clear(){},addWithStats(){},removeWithStats(){}};const c={id:9,name:'list',versions:[],...m};const partial={id:9,name:'list',versions:[],...m};delete partial.removeWithStats;console.log(P.isIPeopleCollection(c),O.isIOrganizationsCollection(c),P.isIPeopleCollection(partial),O.isIOrganizationsCollection({id:9,name:'x',versions:[],add(){},remove(){},clear(){},addWithStats(){},removeWithStats:1}))"
```
→ expect `true true false false` (same object validates under BOTH guards; missing or non-function method fails).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "collection guard add remove", file_pattern: "*collections*", limit: 10 });
```
Observed pass 3: returns both twin guards at 8–12.

## Verdict
Adopt: recognize list-like aggregates by mutation-method surface rather than class or Symbol tag; keep family guards separate even when identical so they can diverge without call-site changes. Adapt method names to your host API. Omit the erased TS payload types (shells). Cross-reference: polymorphic-list-payload-guards (where Collections appear as a payload alternative) and person-aggregate-guard (the richer property+method duck-typing pattern).
