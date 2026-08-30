<!-- capsule-v2 -->
# V1→V2 filter migration — how do legacy operator strings and date-range pseudo-values become normalized v2 filter nodes on read?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where is the boundary that lets old persisted view filters keep working after the domain switches to a different filter AST?

## Read-time migration with per-operator value-shape enforcement
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `mapV1FilterToV2` (:1935-1942: v2-node | v1-group | v1-item dispatch), `v1SymbolOperatorMap` (:65-80), `mapV1FilterItem` (:1991-2059), `mapLegacyDateRangeCondition` (:2061-2106), `normalizeV2FilterNode` (:2115-2170: same rules applied to already-v2 data), `normalizeSelectOptions` legacy `options:[names]` array form (:2198-2205).
**Signature:** `parseViewFilter(raw): RecordFilter | null | undefined` — undefined = column absent (keep default), null = explicitly empty.
**Data Shape:** null-value operators {isEmpty,isNotEmpty}; array operators {isAnyOf,isNoneOf,hasAnyOf,hasAllOf,isNotExactly,hasNoneOf,isExactly}; is/isNot preserve explicit null; everything else with null value DROPS the node.

### Decisive source
```ts
if (record.mode !== 'dateRange') return null;
… // one legacy "within date range" item → TWO concrete nodes:
return { conjunction:'and', items: [
  { fieldId, operator:'isOnOrAfter', value:{mode:'exactDate', exactDate, timeZone} },
  { fieldId, operator:'isOnOrBefore', value:{mode:'exactDate', exactDateEnd, timeZone} } ] };
…
if (operatorsExpectingArray.has(operator)) {
  let value = rawValue;
  if (value == null) return null;                       // array op without array = drop
  if (!Array.isArray(value) && !core.isRecordFilterFieldReferenceValue(value))
    value = [value];                                    // scalar auto-wrapped
  if (Array.isArray(value) && value.length === 0) return null;
}
```

**Flow:** raw JSON string → shape sniffing (v2 items/not/fieldId+operator vs v1 conjunction+filterSet vs flat item) → recursive normalization applying identical value-shape rules to BOTH generations so corrupt entries of any era are dropped uniformly → mapped tree handed to the mapper DTO. Select options get their own twin path (legacy bare-name arrays mint new choice ids + palette colors by index).
**Invariant:** Migration happens at READ time only — writes always persist v2; the tri-state parse result distinguishes "no filter stored" from "stored empty filter". Dropping invalid nodes (never throwing) keeps one bad legacy row from bricking its table load. The symbol map (`=`→is, LIKE→contains, 'IS WITH IN'→isWithIn…) means old clients' saved operators resolve without a data migration.
**Probe:** covered via PostgresTableRepository.spec.ts mapping suites; parse_partial flag = line 1224 only.
**Coverage caveat:** date-range split verified in source; dedicated spec absent for that branch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "mapV1FilterToV2 mapLegacyDateRangeCondition v1SymbolOperatorMap normalizeV2FilterNode", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt read-time migration + uniform value-shape normalization across eras; adapt the operator tables to your DSL versions; keep undefined-vs-null semantics — conflating them erases the empty-filter distinction.
