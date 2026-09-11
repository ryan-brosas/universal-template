<!-- capsule-v2 -->
# Airtable column type map — what is the canonical source→NocoDB type translation table, and which types need special post-processing?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Which remote column types map 1:1 and which become deferred link/lookup/rollup work?

## aTblNcTypeMap + special-case handling
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts:aTblNcTypeMap` (369-391).
**Signature:** `const aTblNcTypeMap: Record<AirtableType, UITypes>` — the single porting surface for type translation.
**Data Shape:** 20 mappings; three special families: `foreignKey → LinkToAnotherRecord`, `count/autoNumber → Decimal`, `lookup → Lookup`, `rollup → Rollup`.

### Decisive source
```ts
const aTblNcTypeMap = {
  foreignKey: UITypes.LinkToAnotherRecord,   // links: deferred to LTAR phase
  text: UITypes.SingleLineText,
  multilineText: UITypes.LongText,
  richText: UITypes.LongText,
  multipleAttachment: UITypes.Attachment,
  checkbox: UITypes.Checkbox,
  multiSelect: UITypes.MultiSelect,
  select: UITypes.SingleSelect,
  collaborator: UITypes.Collaborator,        // multiCollaborator too
  date: UITypes.Date,
  phone: UITypes.PhoneNumber,
  number: UITypes.Decimal,
  rating: UITypes.Rating,
  formula: UITypes.Formula,                  // expression rewrite needed downstream
  rollup: UITypes.Rollup,
  count: UITypes.Rollup,                     // count IS a rollup in NocoDB
  lookup: UITypes.Lookup,
  autoNumber: UITypes.Decimal,
  barcode: UITypes.SingleLineText,           // lossy fallback
  button: UITypes.Button,
};
```

**Flow:** schema phase consults this map while creating columns; `foreignKey` columns skip normal creation and register into `ncLinkMappingTable` for the post-data link phase; formula/lookup/rollup expressions get rewritten against the new table/column ids via the alias maps before materialization.
**Invariant:** unmapped types must fall through to SingleLineText with a migration-skip log (`updateMigrationSkipLog`) — never drop data silently. The two "collapse" pairs (count→Rollup, autoNumber→Decimal, barcode→SingleLineText) are deliberate semantic downgrades that porters should replicate or consciously improve.
**Probe:** no unit test upstream. Source-grounded probe: map literal at `at-import.processor.ts:369-391` is exhaustive over the importer's supported inputs; cross-check with `updateMigrationSkipLog` usage for unmapped types.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "aTblNcTypeMap UITypes foreignKey airtable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit-table approach to type mapping (one literal, greppable); adapt individual mappings to your type system; omit Airtable-specifics once your sources differ. Coverage caveat: no in-repo tests; source-grounded.
