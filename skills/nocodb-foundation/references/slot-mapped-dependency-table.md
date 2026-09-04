<!-- capsule-v2 -->
# Slot-mapped generic dependency table — how do you give heterogeneous event types indexed query columns without per-type migrations?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When many logical fields must live in a fixed physical schema, how do you decide which get real columns and which hide in JSON?

## Queryable-slots + meta-JSON split with typed coercion
**Path/Symbol:** `packages/nocodb/src/helpers/DependencySlotMapper.ts:DependencySlotMapper` (whole 310L; singleton export :310); sibling instance of the same pattern: `src/integrations/integration.store.ts:STORE_DEFINITIONS/IntegrationSlots` (slot_0..slot_9 for AI usage metrics).
**Signature:** `extractSlotFields(dependentType, item): Record<string,any>`; `hydrateSlotFields(dependentType, record): Record<string,any>`; `getSlotId(dependentType, logicalField): string | null`; `getMapping(dependentType)`.
**Data Shape:** physical fields = queryable_field_0..2 (indexed; field_2 = timestamptz for cron nextSyncAt) + meta (JSON). Workflow mapping: nodeType→qf0, triggerId→qf1, nextSyncAt→qf2, {path,nodeId,activationState}→meta. Widget/InterfacePage: only path→meta.

### Decisive source
```ts
// Separate queryable fields from meta fields
if (this.isQueryableField(fieldDef.id)) {
  fields[fieldDef.id] = value;
} else {
  // Store in meta JSON
  metaFields[logicalField] = value;
}
...
// If there are meta fields, stringify and store in meta column
if (Object.keys(metaFields).length > 0) {
  fields[DependencyFields.META] = JSON.stringify(metaFields);
}
```
(:150–:163)

**Flow:** write path — extractSlotFields walks the type's mapping, throws badRequest on missing-required or failed coercion (NUMBER via Number(), ARRAY/OBJECT JSON.parse-if-string then shape check, TIMESTAMP Date-or-ISO, STRING strict typeof), splits values into direct column assignments vs a meta object stringified whole → read path — hydrateSlotFields copies queryable columns first, then parses meta JSON and picks back ONLY mapping-defined keys (unknown keys silently dropped), tolerating parse failures by logging → query path — getSlotId returns the physical column name ONLY for queryable fields; meta fields are unqueryable by construction.
**Invariant:** adding an event type = editing ONE mappings record, zero DDL — but each type gets at most 3 indexed predicates; anything more must ride meta and lose WHERE-clause access. Hydration must round-trip through the SAME mapping or fields strand. The integration-store twin shows the pattern generalizes: named slots with declared types let one table serve many producers.
**Probe:** `cd packages/nocodb && grep -c "QUERYABLE_FIELD" src/helpers/DependencySlotMapper.ts` (=9: enum×3 + comment×2 + isQueryable×3 + mapping refs) and `grep -c "hydrateSlotFields\|extractSlotFields\|getSlotId" src/helpers/DependencySlotMapper.ts` (=3 method definitions).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "DependencySlotMapper extractSlotFields hydrateSlotFields QUERYABLE_FIELD", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mapping-driven slot extraction/hydration + queryable-vs-meta split; adapt slot counts to your index budget; omit if your events have stable dedicated tables. Coverage caveat: grep-pinned only.
