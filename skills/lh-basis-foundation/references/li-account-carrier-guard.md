<!-- capsule-v2 -->
# LI-account carrier guard — How do you validate a lightweight reference carrier that is NOT a DB row?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** when a payload just needs to name *which account* an operation belongs to, how much validation does the kernel apply, and why no `isIDBItem`?

## One-field object-carrier check without row identity
**Path/Symbol:** `core/public-methods/models/instanceProfile/guards.js:isILiAccountIdData` (6–9).
**Signature:** `isILiAccountIdData(data): boolean`.
**Data Shape:** input = any value; valid = truthy non-null object carrying `liAccountId: number`. No `id` field, no positivity requirement, no timestamp ladder, no method surface.

### Decisive source
```js
function isILiAccountIdData(data) {
    const arg = data;
    return Boolean(arg) && typeof arg === 'object' && typeof arg.liAccountId === 'number';
}
```

**Flow:** null/truthiness gate (rejects `null`, `undefined`, `0`, `''`) → object-type gate (note: arrays still pass, per kernel `isObject` convention) → single-field type check on `liAccountId`.
**Invariant:** this guard validates a *carrier*, not a persisted entity — so it deliberately does NOT compose `isIDBItem` and does NOT require `id > 0` like the dbItem root (`isDBId` demands a positive SQLite rowid). A negative or zero `liAccountId` passes because the account id is a LinkedIn-side external number, not a local rowid; the only claim made is "the field is present and numeric". Contrast message-aggregate-guards, where `liAccountId` appears as one whitelisted prop of a full DB entity — same field, deeper context, stronger surrounding contract.
**Probe:** executed against dist module:
```bash
node -e "const g=require('<root>/core/public-methods/models/instanceProfile/guards.js');console.log(g.isILiAccountIdData({liAccountId:7}),g.isILiAccountIdData({liAccountId:'7'}),g.isILiAccountIdData({}),g.isILiAccountIdData(null),g.isILiAccountIdData({liAccountId:-3}))"
```
→ observed `true false false false true` — the negative id PASSES, confirming carriers skip rowid semantics.
**Retrieve (executed pass 5):**
```ts
await mcp.codebase_memory.trace_path({ project: "lh-basis", function_name: "isILiAccountIdData", direction: "inbound" });
```
→ observed `callers_total: 0` within the indexed surface (consumers live in non-indexed dist subtrees); plus pass-5 search `.*(LicenseFeature|LiAccountId).*` → `instanceProfile.guards.isILiAccountIdData 6-9`.

## Verdict
Adopt the minimal truthy-object + typed-field carrier check for cross-system reference handles where you cannot promise local-row identity; keep `isIDBItem` for actual rows so `id > 0` stays meaningful. Adapt the field name/type to your host's handle vocabulary; add `!Array.isArray` if arrays must fail. Omit the LinkedIn account semantics. Coverage: cited file `no_recorded_issue`; probe executed against shipped dist module (no test runner in ingest — standing block).

Cross-references: guard-kernel-composition (`isIDBItem`/`isDBId` root the row-entity recipe this carrier deliberately skips), message-aggregate-guards (`liAccountId` inside a full aggregate whitelist).
