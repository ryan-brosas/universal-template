<!-- capsule-v2 -->
# Cycle-aware serializability + duplicate detection — how do you prove test data is JSON-safe and reject duplicated cases without false positives?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the tester decide a test case is serializable (skipping the dup check otherwise) and canonicalize it for duplicate detection?

## isSerializable path-scoped cycle check
**Path/Symbol:** `lib/shared/serialization.js:isSerializable(val, seenObjects)` (:33–78) + `isSerializablePrimitiveOrPlainObject` (:14–20).
**Signature:** `isSerializable(value): boolean`.
**Data Shape:** serializable = primitives (`null`, string, boolean, number) ∪ arrays ∪ objects with `val.constructor === Object`; EVERYTHING else (functions, RegExp, class instances) is not.

### Decisive source
```js
if (typeof val[property] === "object" && val[property] !== null) {
  if (!isSerializable(val[property], new Set([...seenObjects, val]))) return false;
}
// comment: new Set per level — `val` must not reappear ON THIS PATH,
// but may be SHARED across paths (DAGs pass, cycles fail)
```

**Flow:** depth-first over own enumerable properties; each object level threads `seenObjects + val` into a FRESH set.
**Invariant:** the per-path (not global) visited set is the whole point — a globally-shared memo would flag shared sub-objects as circular; a no-memo walk would infinitely recurse. Note the subtle gap: nested property values are checked with `isSerializablePrimitiveOrPlainObject` FIRST at their level but recursion only descends when the child is an object — so a non-plain constructor inside an array IS caught by the primitive gate at that level. Consumers rely on false-negatives being impossible: anything returning true round-trips through `json-stable-stringify-without-jsonify`.
**Probe:** `tests/lib/shared/serialization.js` (25 assertions incl. DAG-reuse-passes vs cycle-fails).

## Duplicate test-case detection
**Path/Symbol:** `lib/rule-tester/rule-tester.js:checkDuplicateTestCase` (:494–517) + `duplicationIgnoredParameters = {name, errors, output}` (:375).
**Flow:** skip silently when `!isSerializable(item)` → stable-stringify with a replacer that strips ignored keys ONLY at the top level (`item !== this` guard) → assert unseen → add.
**Invariant:** top-level-only stripping means two cases differing in a NESTED `errors` entry still count as duplicates of each other only if everything else matches; non-serializable properties (options/plugins/settings/parserOptions) disable the check for THAT case rather than throwing — dup protection must never break legitimate dynamic tests.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (:4629+ "duplicate test cases" matrix; :5058/:5089/:5124/:5155 non-serializable escape hatches — settings/parserOptions/plugins/options).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "isSerializable checkDuplicateTestCase duplicationIgnoredParameters", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.serialization.isSerializable" });
```

## Verdict
Adopt the path-scoped visited-set verbatim for any JSON-safety gate; adapt which top-level keys are stripped for your dup detector; omit stringify choice details.
