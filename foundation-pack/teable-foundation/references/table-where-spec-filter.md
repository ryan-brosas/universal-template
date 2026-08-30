<!-- capsule-v2 -->
# Table where-filter visitor — how do table-level specs compile to `table_meta` WHERE clauses, and why does the deleted-state leak into EXISTS subqueries?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A porter needs the four provision-state ladders, the loud-fail contract on mutation specs, and the incoming-reference EXISTS predicate.

## state-gated default conditions + spec-info describe + unsupported-spec refusal
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/visitors/TableWhereVisitor.ts` — constructor (96–109), `visitTableByIncomingReferenceToTable` (194–218), `visitTableByIds` empty-list guard (220–227), ~40 loud-fail visit methods (122–716); direct test `TableWhereVisitor.spec.ts` :29–170 ('adds the default…' :35, 'handles table id lists, including the empty-list validation path' :117, 'returns validation errors for unsupported specs' :166) and clone/and/or/not :336.
**Signature:** `new TableWhereVisitor(state: 'active'|'activeWithPending'|'activeAnyProvision'|'deleted')`; produces `ITableMetaWhere` Kysely closures over `table_meta`.

### Decisive source
```ts
if (state === 'active')            { deleted is null; provision_state = 'ready' }
else if (state === 'activeWithPending') { deleted is null; provision_state IN ('ready','pending') }
else if (state === 'activeAnyProvision') { deleted is null }              // no provision gate
else if (state === 'deleted')      { deleted is not null }                // NO provision gate either
// incoming reference (state-dependent target_field predicate!):
const targetFieldDeletedPredicate = this.state === 'deleted'
  ? sql`"target_field"."deleted_time" is not null`
  : sql`"target_field"."deleted_time" is null`;
exists (select 1 from "reference"
  inner join "field" as "source_field" on source_field.id = reference.from_field_id
  inner join "field" as "target_field" on target_field.id = reference.to_field_id
  where source_field.table_id = ${incomingReferenceToTableId}
    and ${targetFieldDeletedPredicate}
    and target_field.table_id = table_meta.id)
// every mutation/field-update spec: return err(validation('XSpec is not supported for table filters'))
```

**Flow:** constructor seeds the two default conditions per state → each supported selector adds its condition AND merges a `describe()` info record ({specName, tableId|baseId|nameLike|...}) for diagnostics → mutation specs refuse loudly instead of silently matching nothing → `and/or/not` combine via AbstractSpecFilterVisitor; `clone()` gives a fresh accumulator.
**Invariant:** TWO soft-delete axes are filtered independently — the TABLE's own `deleted_time` and the REFERENCED FIELD's `deleted_time` inside the EXISTS; the deleted-state query must match fields deleted at the same time as tables or cross-table references vanish/appear incorrectly. Empty id-list REFUSES (`unexpected`) rather than compiling `in ()` (SQL syntax error) — never emit an empty IN.
**Probe:** `TableWhereVisitor.spec.ts` :141–164 pins both active and deleted describe() outputs for the incoming-reference filter; :166–335 enumerates the unsupported-spec error ladder.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableWhereVisitor visitTableByIncomingReferenceToTable activeWithDeleted provision_state", limit: 8 });
```

## Verdict
Adopt the four-state constructor ladder and the dual soft-delete EXISTS; adapt the provision_state vocabulary to host lifecycle states. The loud-fail-on-mutation-spec pattern (err-not-empty-match) is the reusable primitive — port it wherever a read-model visitor shares an interface with a write-model visitor.
