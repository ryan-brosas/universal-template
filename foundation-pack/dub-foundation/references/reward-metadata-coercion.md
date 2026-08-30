<!-- capsule-v2 -->
# Metadata value coercion — operator-driven typing of loose JSON before comparison

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** Lead/sale metadata is schemaless JSON — how does a stringy value become comparable for each operator class?

## Operator-class-driven normalization
**Path/Symbol:** `apps/web/lib/api/rewards/reward-condition-metadata.ts:prepareMetadataFieldValue` (:50-88) + private `toNumber` (:7-34), `toString` (:36-38).
**Signature:** `prepareMetadataFieldValue(fieldKey: unknown, condition: RewardCondition): string | number | ... | undefined`.
**Data Shape:** input = raw JSON scalar from `<lead|sale>.metadata[key]`; output typed per operator class or undefined (fail-closed).

### Decisive source
```ts
// Metadata conditions do not support in / not_in and other non-metadata operators.
if (!METADATA_CONDITION_OPERATORS.includes(operator)) {
  return undefined;
}

// Pattern text operators always compare against a stringified metadata value.
if (
  operator === "starts_with" ||
  operator === "ends_with" ||
  operator === "contains" ||
  operator === "not_contains"
) {
  return toString(fieldKey);
}

// Numeric operators require a parsed number, or undefined when coercion fails.
if (METADATA_NUMBER_CONDITION_OPERATORS.includes(operator)) {
  return toNumber(fieldKey);
}

// For equals_to / not_equals with a numeric condition value, prefer number coercion.
if (typeof conditionValue === "number") {
  const numeric = toNumber(fieldKey);
  return numeric !== undefined ? numeric : toString(fieldKey);
}

// All other operators use string comparison.
return toString(fieldKey);
```
(reward-condition-metadata.ts :60-87)

**Flow:** reject non-metadata operators (in/not_in unsupported on metadata ⇒ undefined ⇒ condition fails) → text-pattern operators get String coercion unconditionally → the four numeric comparators get toNumber (booleans/arrays/whitespace/non-numeric strings ⇒ undefined) → equals_to/not_equals type-align against the CONDITION value: numeric condition ⇒ try numeric first then fall back to string; otherwise plain string.
**Invariant:** toNumber's rejection list is load-bearing — booleans and arrays NEVER coerce (no `Number(true)`=1, no `Number([5])`=5 surprises); empty/whitespace strings and NaN strings yield undefined so the numeric comparator's `fieldValue===undefined` gate fires. The doc comment states the contract: "the return type is aligned with condition.value so strict equality checks compare like types."
**Probe:** deterministic probes (repo root): `grep -c 'Number.isNaN' apps/web/lib/api/rewards/reward-condition-metadata.ts` → 3; `grep -n 'METADATA_CONDITION_OPERATORS.includes' apps/web/lib/api/rewards/reward-condition-metadata.ts` → :61; `grep -n 'METADATA_NUMBER_CONDITION_OPERATORS.includes' apps/web/lib/api/rewards/reward-condition-metadata.ts` → :76; `grep -n 'Array.isArray(fieldKey)' apps/web/lib/api/rewards/reward-condition-metadata.ts` → :20; direct-test anchors in reward-conditions.test.ts: `grep -n 'test("returns null when metadataField is empty"' apps/web/tests/rewards/reward-conditions.test.ts` → :2288; metadata edge describes at :2288/:2313/:2340/:2370.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "prepareMetadataFieldValue", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt operator-class-driven coercion with the strict rejection list and condition-value-typed equality alignment. Adapt METADATA_*_OPERATORS tables to host. Omit nothing.
