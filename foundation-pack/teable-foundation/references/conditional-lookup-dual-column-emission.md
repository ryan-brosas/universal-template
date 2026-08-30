<!-- capsule-v2 -->
# conditional-lookup-dual-column-emission — Why does one conditional CTE expose BOTH conditional_lookup_<id> and conditional_rollup_<id> columns?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a ConditionalRollup is also isLookup, which CTE serves which reader?

## Lookup branch emits both aliases; rollup branch only its own; readers pick per field type
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:generateConditionalLookupFieldCteForScope` — dual select (:1856-1866 equality plan; :1894-1900 fallback) + reader dispatch `field-select-visitor.ts` (:279-286 column choice).
**Signature:** `cqb.select(raw(joinAlias."reference_value" as "conditional_lookup_<id>")); if (field.type === ConditionalRollup) cqb.select(raw(... as "conditional_rollup_<id>"))`.
**Data Shape:** same aggregate SQL aliased twice; reader: `field.type === FieldType.ConditionalRollup ? conditional_rollup_<id> : conditional_lookup_<id>`.

### Decisive source
```ts
cqb.select(cqb.client.raw(`${joinAlias}."reference_value" as "${lookupAlias}"`));
if (field.type === FieldType.ConditionalRollup) {
  cqb.select(cqb.client.raw(`${joinAlias}."reference_value" as "${rollupAlias}"`));
}
...
// reader:
const column = field.type === FieldType.ConditionalRollup
  ? `conditional_rollup_${field.id}`
  : `conditional_lookup_${field.id}`;
```

**Flow:** a ConditionalRollup marked lookup can be READ through two visitors (FieldSelectVisitor.checkAndSelectLookupField vs visitConditionalRollupField) → whichever runs, the column name it expects exists on the SAME joined CTE → no second aggregate is computed.
**Invariant:** the duplication is an interface shim, not redundancy — emitting only one alias makes one of the two read paths emit a missing-column error at execution. Rollup-only fields skip the extra alias.
**Probe:** static byte-exact: `grep -n 'as "\${rollupAlias}"' field-cte-visitor.ts` → :1861/:1899.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"conditional_rollup_","limit":5,"detail":"ids"}'
```

## Verdict
Adopt dual-alias emission for dual-reader fields. Adapt naming. Omit nothing.
