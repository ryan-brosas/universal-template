<!-- capsule-v2 -->
# PAS timestamp ladder — Which sync timestamps must exist, and which one is allowed to be absent?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** an entity carries `createdAt`/`updatedAt`/`actualAt`/`sentAtToPAS` — which are mandatory `Date` instances, why is one optional, and how does the conjunction ladder compose?

## Three required Dates + one optional field over a four-predicate conjunction
**Path/Symbol:** `core/public-methods/models/helpers/guards/dates.js` — `isISentAtToPASDate` (11–13), `isICreatedAtDate` (14–16), `isIUpdatedAtDate` (17–19), `isIActualAtDate` (20–22), `isISentAtToPASDates` (23–25).
**Signature:** each `(data): boolean`; composite `isISentAtToPASDates(data): boolean`.
**Data Shape:** required trio `createdAt`, `updatedAt`, `actualAt` must each be `instanceof Date`; optional `sentAtToPAS` may be `undefined` OR a `Date` — any other value (including ISO strings) falsifies.

### Decisive source
```js
function isISentAtToPASDate(data) {
    return isObject(data) && (data.sentAtToPAS === undefined || data.sentAtToPAS instanceof Date);
}
function isICreatedAtDate(data)  { return isObject(data) && data.createdAt instanceof Date; }
function isIUpdatedAtDate(data)  { return isObject(data) && data.updatedAt instanceof Date; }
function isIActualAtDate(data)   { return isObject(data) && data.actualAt instanceof Date; }
function isISentAtToPASDates(data) {
    return isICreatedAtDate(data) && isIUpdatedAtDate(data) &&
           isISentAtToPASDate(data) && isIActualAtDate(data);   // order irrelevant: pure ∧
}
```

**Flow:** every predicate re-checks `isObject` independently, so each is callable alone; the composite is a flat four-way conjunction with no short-circuit-dependent ordering and no mutation.
**Invariant:** the *semantics* encoded here: local row-lifecycle stamps (`createdAt`/`updatedAt`) and data-freshness stamp (`actualAt`) are ALWAYS present on a synced entity, while `sentAtToPAS` records an outbound push that may simply not have happened yet — hence `undefined` is legal but a wrong-typed value never is. `instanceof Date` means these guards validate in-process objects only; JSON-revived payloads carry strings and will fail (porters must revive first). Note `actualAt` also gates hash→memberId enrichment in `Hash.extractMemberIdData`, where it is carried through only when already a valid Date.
**Probe:** executed against dist module:
```bash
node -e "const d=require('<root>/core/public-methods/models/helpers/guards/dates.js');const now=new Date();console.log(d.isICreatedAtDate({createdAt:now}),d.isICreatedAtDate({createdAt:now.toISOString()}),d.isISentAtToPASDates({createdAt:now,updatedAt:now,actualAt:now}),d.isISentAtToPASDates({createdAt:now,updatedAt:now,sentAtToPAS:now,actualAt:now}),d.isIActualAtDate({actualAt:null}))"
```
→ observed `true false true true false`: ISO string fails, absent-but-legal `sentAtToPAS` passes, `null` actualAt fails.
**Retrieve (executed pass 5):**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "lh-basis", paths: ["core/public-methods/models/helpers/guards/dates.js"] });
```
→ observed `no_recorded_issue`, freshness `metadata_match` @ gen 2026-08-23T00:11:49Z.

## Verdict
Adopt per-field timestamp predicates that distinguish "field not yet set" (`=== undefined`) from "field wrong type" (falsify), composed by pure conjunction into the entity's timestamp contract. Adapt the stamp names to your sync domain. Omit the PAS (LinkedIn push-target) concept if your host has no outbound-push ledger — then the optional slot disappears and the ladder shrinks to its required core. Coverage: file fully indexed (`no_recorded_issue`); probe executed against shipped dist module (no test runner in ingest — standing block).

Cross-references: guard-kernel-composition (cites this ladder as its composition example — this capsule owns the timestamp semantics proper); external-identifier-type-algebra (`isIActualAtDate` reuse inside `extractMemberIdData`).
