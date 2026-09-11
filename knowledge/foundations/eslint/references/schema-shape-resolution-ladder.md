<!-- capsule-v2 -->
# Schema-shape resolution ladder — how do you turn a rule's `meta.schema` (array / object / false / absent) into one validator contract?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does Config.getRuleOptionsSchema normalize four authoring styles into a single JSON-schema-or-null, and how does the tester police the degenerate forms?

## getRuleOptionsSchema
**Path/Symbol:** `lib/config/config.js:getRuleOptionsSchema(rule)` (:177–213) + static forwarder (:774–776) + noOptionsSchema constant (:33).
**Signature:** `getRuleOptionsSchema(rule): object|null` — null ONLY for explicit `schema:false`.
**Data Shape:** array form wraps as `{type:"array", items: schema, minItems:0, maxItems: schema.length}`; empty array ⇒ no-options schema (`{type:"array",minItems:0,maxItems:0}`); missing meta/schema ⇒ same default; non-array-object passes through untouched; anything else throws TypeError.

### Decisive source
```js
if (Array.isArray(schema)) {
  if (schema.length) return { type: "array", items: schema, minItems: 0, maxItems: schema.length };
  return { ...noOptionsSchema };          // `schema: []` = "no options" — NOT an error
}
// `schema:<object>` assumed valid JSON Schema; top-level `rule.schema` is IGNORED (meta only)
```

**Flow:** meta absent/undefined ⇒ default no-options clone → false ⇒ null (validator skipped entirely) → type check → array/object branch.
**Invariant:** `[]`, absent, and undefined are EQUIVALENT (accept zero options) but `false` is categorically different: it means "don't validate at all", which the tester treats as the only legitimate opt-out. The tester separately FORBIDS `schema:{}` — an empty object validates nothing yet looks intentional, so it's rejected with guidance ("set meta.schema to an array or non-empty object… or false to opt out") because ajv cache-keying on own-enumerable props would make inherited-property schemas collide. Fresh-object returns (`{...noOptionsSchema}`) prevent callers from mutating the shared constant.
**Probe:** `tests/lib/config/config.js` (:120–212 static getRuleOptionsSchema table incl. array-wrap shape, false⇒null :183, throw list `[null,true,0,1,"","always",()=>{}]` :191, top-level-ignored); `tests/lib/rule-tester/rule-tester.js` (:2039/:2061/:2092 "`schema: {}` is a no-op"-family rejections incl. non-enumerable/inherited schemas).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getRuleOptionsSchema noOptionsSchema meta.schema", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config.getRuleOptionsSchema" });
```

## Verdict
Adopt the four-way ladder for any rule/plugin options system; keep the {}-is-a-no-op rejection — it catches a real class of authoring mistakes; adapt the guidance text.
