<!-- capsule-v2 -->
# display-value admission ladder — when an Airtable primary field can't be a display value, what replaces it?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** An import job must never die over a cosmetic choice like "which column is the title" — what eligibility predicate and fallback ladder pick the display value?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts:nocoSetPrimary` (isEligibleDisplayValue :1494–:1510; ladder :1516–:1604; Title minting :1552–:1580).
**Signature:** closure `isEligibleDisplayValue(col): boolean`; whole ladder wrapped in per-table try/catch → logWarning, never throw.
**Data Shape:** eligible = ¬pk ∧ ¬system ∧ isSupportedDisplayValueColumn ∧ ¬createdOrLastModifiedTime ∧ ¬(Formula ∧ formula/formula_raw === '""'); taken-set = lowercased titles∪column_names.

### Decisive source
```ts
// Airtable allows primary field types NocoDB cannot use as a display value
// (long text), and every imported formula lands as a `""` placeholder - the
// real expression survives only in the field description - so a formula
// display value would render blank on every record. Mirrors
// mapDefaultDisplayValue's checks, which already ran at tableCreate.
const isEligibleDisplayValue = (col) => !!col && !col.pk && !isSystemColumn(col)
  && isSupportedDisplayValueColumn(col) && !isCreatedOrLastModifiedTimeCol(col)
  && !(col.uidt === UITypes.Formula && (col.colOptions?.formula === '""' || ...));
...
} catch (e) { logWarning(`Failed to configure display value for ${aTbl.name}`); }
```

**Flow:** refresh schema FIRST (link/lookup/rollup columns exist only post-tableCreate) → try primary if eligible → else first OTHER eligible column with a warning naming the rejected reason → else MINT a new SingleLineText column titled `Title`, `Title_2`, … against a lowercase taken-set of existing titles+column_names (deliberately NOT nc_getSanitizedColumnName: its generator keys off the pre-create table name and tableCreate prefixes table_name, so it would collide) → columnSetAsPrimary → skip entirely if mapDefaultDisplayValue already set a pv → ANY throw logs a warning and continues to the next table because a display value is nice-to-have and the outer catch would drop every created table.
**Invariant:** (1) Cosmetic failures must never abort a long import — degrade per-table. (2) The `""` formula placeholder check exists because imported formulas are blank until lazily parsed; using one as display value renders every record blank. (3) Schema refresh precedes eligibility scanning or link/lookup columns don't exist yet as candidates. (4) Name-minting bypasses the standard sanitizer BY DESIGN (prefix-keyed generator collision).
**Probe:** `grep -n "title = \`Title_" …at-import.processor.ts` → :1563; `sed -n '1494,1510p'` predicate verbatim. Upstream ships mock-response fixtures (mockResponses/readDisplayValue.ts :1–:137) but no unit runner wired for the processor.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "nocoSetPrimary display value at-import processor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt eligibility predicate + three-rung fallback + warn-not-throw posture; adapt type support lists; omit mock fixtures (upstream test scaffolding).
