<!-- capsule-v2 -->
# Scalar taxonomy guards — How do you validate closed string vocabularies at runtime without TS enums?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** when a domain value is a closed set of string literals (statuses, tiers, categories), what does the kernel's membership guard look like and where do the literal lists live?

## Closed-list membership predicates beside their constant arrays
**Path/Symbol:** `core/public-methods/models/tasks/guards.js:isTTaskStatus` (7–9) + `core/public-methods/models/tasks/constants.js` (`taskStatuses`, `periodicTasksTypes`, line 7/6); `core/public-methods/models/people/EmailType/guards.js:isEmailType` (6–8); `core/public-methods/models/limits/guards.js:isLicenseFeatureSet` (6–8).
**Signature:** `isTTaskStatus(data): boolean`; `isEmailType(value): boolean`; `isLicenseFeatureSet(value): boolean`.
**Data Shape:** each predicate accepts any value and answers strict membership over a closed literal list; the lists live either in a sibling constants module (`taskStatuses = ['unscheduled','scheduled','failed']`, `periodicTasksTypes = ['collectSSIScores']`) or inline in the guard body (`['pro','standard']`, `'personal'|'business'`).

### Decisive source
```js
// tasks/constants.js
exports.periodicTasksTypes = ['collectSSIScores'];          // one-element taxonomy
exports.taskStatuses = ['unscheduled', 'scheduled', 'failed'];
// tasks/guards.js
function isTTaskStatus(data) { return constants_1.taskStatuses.includes(data); }
// people/EmailType/guards.js
function isEmailType(value) { return value === 'personal' || value === 'business'; }
// limits/guards.js
function isLicenseFeatureSet(value) { return ['pro', 'standard'].includes(value); }
```

**Flow:** any input → strict list-membership test → boolean. No coercion, no defaulting, no error: an unknown status (`'running'`), wrong case (`'Personal'`), or non-string (`undefined`) simply fails.
**Invariant:** the runtime vocabulary is the ARRAY OF LITERALS itself, not a TS enum — the compiled JS keeps only the array, so the guard and the list must stay co-located (same folder or same file) or they will drift. Membership is case-sensitive and type-strict (`Array.includes` uses SameValueZero).
**Probe:** executed against dist modules:
```bash
node -e "const t=require('<root>/core/public-methods/models/tasks/guards.js');const e=require('.../people/EmailType/guards.js');const l=require('.../models/limits/guards.js');console.log(t.isTTaskStatus('scheduled'),t.isTTaskStatus('running'),t.isTTaskStatus(undefined),e.isEmailType('business'),e.isEmailType('Personal'),l.isLicenseFeatureSet('pro'),l.isLicenseFeatureSet('enterprise'))"
```
→ observed `true false false true false true false`.
**Retrieve (executed pass 5):**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", name_pattern: ".*(TaskStatus|EmailType|LicenseFeature).*" });
```
→ observed 8 rows incl. `tasks.guards.isTTaskStatus 7-9`, `EmailType.guards.isEmailType 6-8`, `limits.guards.isLicenseFeatureSet 6-8`.

## Verdict
Adopt literal-array + includes membership as the runtime source of truth for closed vocabularies, with the guard living next to its list. Adapt: prefer exporting the array so hosts can build UI pickers from the same constant (the kernel exports `taskStatuses` but keeps license/email lists private inside the guards). Omit the specific LinkedIn/task vocabularies. Coverage: all three cited files `no_recorded_issue`; no test runner in ingest — probe evidence above was executed against shipped dist modules.

Cross-references: interval-and-limit-guards (the 34-kind `ALL_DEFAULT_LIMIT_TYPES` list this pattern scales up to), external-identifier-type-algebra (`Type.Member.all` arrays feeding `.is` membership).
