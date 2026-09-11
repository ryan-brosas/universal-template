<!-- capsule-v2 -->
# Redundant-inline-config detection — how do you warn that an inline rule tweak changed nothing, without false positives on option identity?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the linter decide an inline `/* eslint rule: "error" */` comment is redundant, and what deep-comparison makes option equality safe?

## addProblemIfSameSeverityAndOptions + containsDifferentProperty
**Path/Symbol:** `lib/linter/linter.js:addProblemIfSameSeverityAndOptions` (:159–211) + `lib/shared/option-utils.js:containsDifferentProperty(input, original)` (:16–61).
**Signature:** `containsDifferentProperty(input, original): boolean` — true iff any property DIFFERS.
**Data Shape:** compares structurally with type/Array-ness mismatch short-circuit; object comparison is KEY-SET + per-key recursion (extra keys ⇒ different); primitives compare by `!==`... via final `return true`.

### Decisive source
```js
const existingConfig = existingConfigRaw ? asArray(existingConfigRaw) : ["off"];
if (normalizeSeverityToString(existingConfig[0]) !== normalizeSeverityToString(ruleOptions[0])) return;
if ((existingConfig.length === 1 && ruleOptions.length === 1) || existingSeverity === "off")
  message = `Unused inline config ('${ruleId}' ${alreadyConfigured}).`;
else if (!containsDifferentProperty(ruleOptions.slice(1), existingConfig.slice(1)))
  message = `Unused inline config ('${ruleId}' ${alreadyConfigured} with the same options).`;
```

**Flow:** severity gate first (string-normalized: 2/"2"/"error" collapse) → no-options fast path → deep option compare → emit warning/error at the comment location through the normal report path.
**Invariant:** the deep comparator treats `{a:undefined}` vs missing key as DIFFERENT (key-count check) and `null` vs `{}` as different (type branch) — deliberately strict because JSON-config semantics make those distinguishable; a naive deepEqual would silently accept configs ajv would reject. Severity-only inline comments are redundant even when file-level options exist ONLY IF options were also given inline and match — hence the two-message split. The comparator recurses arrays element-wise so `[severity, {opt}]` shapes compare correctly.
**Probe:** `tests/lib/shared/option-utils.js` (:22–88 table incl. `[{a:[void 0]},{a:[0]}] ⇒ true` :60, identical nested false); `tests/lib/linter/linter.js` unused-inline-config matrix (:4137–4335 message variants asserted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "addProblemIfSameSeverityAndOptions containsDifferentProperty", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.option-utils.containsDifferentProperty" });
```

## Verdict
Adopt for config-linting features ("you configured this twice"); adapt message text; reuse the comparator anywhere JSON-ish option identity matters — but re-read its undefined-vs-missing stance first.
