<!-- capsule-v2 -->
# Rule options pipeline — how do `meta.defaultOptions`, schemas, and severity normalization compose into the options a rule's create() receives?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How are user-supplied rule options validated, defaulted, and delivered?

## Schema forms + validator caching
**Path/Symbol:** `lib/config/config.js:getRuleOptionsSchema` (:177–214) + `getOrCreateValidator` (:410–424).
**Signature:** static `Config.getRuleOptionsSchema(rule): object|null`; validators cached in a module-level `WeakMap` keyed by the rule object.
**Data Shape:** `meta.schema` may be absent (⇒ no-options schema `{type:"array",minItems:0,maxItems:0}`), `false` (explicit opt-out ⇒ null), an array (positional items, `maxItems: schema.length`), or a plain JSON-Schema object. RuleTester additionally rejects empty-object schemas (`schema:{}` is a no-op; use `false` to opt out).

### Decisive source
```js
if (Array.isArray(schema)) {
  if (schema.length) {
    return { type: "array", items: schema, minItems: 0, maxItems: schema.length };
  }
  return { ...noOptionsSchema };   // schema:[] == no options allowed
}
```

**Flow:** resolve schema per rule → compile once via ajv (`getOrCreateValidator`) → validate only the *options slice* (`ruleOptions.slice(1)`) for enabled rules.
**Invariant:** disabled rules (severity 0) skip validation entirely so users can park any value under `"off"` without schema errors; the WeakMap is keyed by rule identity, so recompiles only happen across distinct module instances.
**Probe:** `tests/lib/config/config.js` (schema forms), `tests/lib/rule-tester/rule-tester.js` (`schema:{}` rejection).

## defaultOptions deep-merge
**Path/Symbol:** `lib/shared/deep-merge-arrays.js` (:1–62) applied in `lib/config/config.js:#normalizeRulesConfig` (:608–633) and again inline in `lib/linter/linter.js:getRuleOptions` (:446–451).
**Signature:** `deepMergeArrays(defaultOptions = [], userOptions = []): merged[]`.
**Data Shape:** arrays merge element-wise; plain objects deep-merge key-by-key (user wins); primitives replace.

### Decisive source
```js
// #normalizeRulesConfig — runs at Config construction:
const slicedOptions = ruleConfig.slice(1);
const mergedOptions = deepMergeArrays(rule?.meta?.defaultOptions, slicedOptions);
if (mergedOptions.length) ruleConfig = [ruleConfig[0], ...mergedOptions];
```

**Flow:** config construction merges defaults into stored rule configs; the linter's `getRuleOptions` merges *again* when delivering `context.options` (idempotent because defaults ⊆ merged result), covering inline-config paths that bypass the constructor.
**Invariant:** user options win at every level of nesting — a porter who shallow-spreads instead of deep-merging loses nested partial overrides like `[{ a: { x: 1 } }]` vs `[{ a: { y: 2 } }]`. Severity normalization (`"warn"`→1 etc.) precedes merging so downstream code sees numeric severities only.
**Probe:** `tests/lib/config/config.js` + `tests/lib/linter/linter.js` (defaultOptions application cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getRuleOptionsSchema getOrCreateValidator deepMergeArrays getRuleOptions", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config.Config.getRuleOptionsSchema" });
```

## Verdict
Adopt the four-form schema resolution, identity-keyed validator cache, disabled-rule validation skip, and recursive array/object option merging; adapt ajv usage and severity vocabulary to host; omit RuleTester-specific schema strictness unless porting the harness too.
