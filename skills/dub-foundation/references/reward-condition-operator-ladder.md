<!-- capsule-v2 -->
# Condition operator ladder — twelve operators with type-guarded failure modes

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What does each comparison operator do when field/value types don't line up?

## Ordered operator dispatch, fail-closed by construction
**Path/Symbol:** `apps/web/lib/partners/evaluate-reward-conditions.ts:evaluateCondition` (:108-224).
**Signature:** `evaluateCondition({condition, fieldValue}): boolean` — terminal `return false` for unknown operators.
**Data Shape:** fieldValue arrives pre-typed by resolveConditionFieldValue/prepareMetadataFieldValue; condition.value is author-supplied JSON.

### Decisive source
```ts
// Contains
if (condition.operator === "contains") {
  if (typeof fieldValue !== "string" || typeof condition.value !== "string") {
    return false;
  }

  const trimmedValue = condition.value.trim();

  if (trimmedValue === "") {
    return false;
  }

  return String(fieldValue).includes(trimmedValue);
}
```
(evaluate-reward-conditions.ts :152-164; the same trim-empty-fail shape repeats for not_contains :167-179)

**Flow (12 operators in source order):** equals_to/not_equals use strict `===`/`!==` on RAW values → starts_with/ends_with require BOTH sides string AND non-empty value else false → contains/not_contains coerce fieldValue via String() but still demand string value + non-empty after trim → in requires Array.isArray(value) (empty array ⇒ no match ⇒ false) / not_in additionally rejects EMPTY arrays to false (so "not_in []" is never vacuously true) → greater_than/greater_than_or_equal/less_than/less_than_or_equal coerce both sides through Number().
**Invariant:** every malformed input fails CLOSED (false), including the asymmetric not_in empty-array rule — an empty allowlist blocks, an empty blocklist does NOT permit. Strict equality on equals_to means `"1" !== 1`: metadata values must arrive type-aligned via prepareMetadataFieldValue or the condition silently never matches. Unknown operator ⇒ final `return false`.
**Probe:** deterministic probes (repo root): `grep -c 'return false;' apps/web/lib/partners/evaluate-reward-conditions.ts` → 10; `grep -c 'condition.value === ""' apps/web/lib/partners/evaluate-reward-conditions.ts` → 2 (starts_with :130 + ends_with :143); `grep -n 'Array.isArray(condition.value)' apps/web/lib/partners/evaluate-reward-conditions.ts` → :183 and :194; direct-test anchors: suite describe blocks at equals_to :355, not_equals :417, in :479, not_in :541 ("should not match when condition value is an empty array" :602), contains :648, starts_with :795, ends_with :881, numeric ladders :965-1330.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "evaluateCondition", limit: 5, fields: ["signature", "name", "file"] });
```
(two same-named nodes exist — route by file `evaluate-reward-conditions.ts`; the twin in evaluate-application-requirements.ts is a different contract.)

## Verdict
Adopt the fail-closed operator ladder incl. the not_in empty-array asymmetry and strict-equality typing. Adapt operator vocabulary. Omit nothing.
