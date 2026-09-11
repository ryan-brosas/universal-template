<!-- capsule-v2 -->
# AST column-inclusion strategy chain — which rung decides whether one column enters the response, and why does order beat conditions?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Column inclusion depends on view visibility, system flags, API version, hidden-column mode, fields lists, sort/filter and row-color columns — how do you compose all gates without the branches drifting apart?

## Ordered first-match-wins strategy array reproducing a legacy if/else ladder
**Path/Symbol:** `packages/nocodb/src/helpers/getAstColumnStrategy.ts:columnAstStrategies` (:269-282) + `resolveColumnAst` (:288-301).
**Signature:** `interface ColumnAstStrategy { name: string; match(ctx: ColumnAstContext, input: ColumnAstInput): boolean; resolve(ctx, input): AstResult }`; `export function resolveColumnAst(ctx: ColumnAstContext, input: ColumnAstInput): AstResult`.
**Data Shape:** `AstResult = boolean | number | null | undefined | Ast` (strategies may return false/0/undefined = "not in response", 1/true = scalar, or a nested Ast); narrowed back to exported `Ast = { [key: string]: 1 | true | null | Ast }` by the caller so the shape stays assignable to `nocoExecute`'s FieldRequest.

### Decisive source
```ts
export const columnAstStrategies: ColumnAstStrategy[] = [
  metaFieldStrategy,
  sortFilterFieldStrategy,
  rowColorButtonFieldStrategy,
  v3PrimaryKeyFieldStrategy,
  v3SystemFieldStrategy,
  createdModifiedByFieldStrategy,
  orderFieldStrategy,
  deletedFieldStrategy,
  hiddenColumnFieldStrategy,
  viewVisibilityFieldStrategy,
  explicitFieldsFieldStrategy,
  defaultFieldStrategy,
];
```
(:269-282 — "array order IS the priority (first match wins), reproducing the original getAst if/else ladder exactly. `defaultFieldStrategy` is the terminal catch-all and must stay last.")

**Flow:** per column, `resolveColumnAst` finds the FIRST strategy whose match() returns true (guaranteed by the terminal default), calls its resolve(), debug-logs under `nc:ast:<name>` via cached per-strategy debuggers.
**Invariant:** Each `match` encodes ONLY its own rung condition — it must NOT re-encode "and no earlier rung matched"; ordering supplies the exclusion. Reordering the array silently changes API response shapes.

### Porting traps (each verified against source)
- **The 12 rungs in order:** meta (false) → view sort/filter columns (pass through nested `value`) → row-color/button-filter columns (true) → v3 PK (always true) → v3 system non-PK except Created/LastModified time (false) → Created/LastModified-By (false) → Order system col (only when extractOrderColumn/getHiddenColumn/named-in-fields) → soft-delete (false) → getHiddenColumn mode (system guard with non-has-many system-link + pk exceptions) → view visibility (`allowedCols[col.id] || (allowRequestedHiddenFields && isInFields)` AND system-gate AND fields-gate AND value) → explicit fields list (v3 keeps PK even unlisted) → default everything.
- **`allowRequestedHiddenFields` is opt-in for authenticated link-picker paths only** — "never public (would leak hidden values; see the DESIGN NOTE in public-datas.service.ts)" (:68-74). A porter who defaults it to true opens a leak.
- **LTAR custom display values ride `value`, not the strategies:** sortFilter resolve passes the nested AST through; without an override legacy `true` (pk+pv) is correct; lookups keep scalar 1 and the EE query client widens them (:108-118).
- **In-file anchors:** `grep -c "name: '" src/helpers/getAstColumnStrategy.ts` → `12`; `grep -n 'must stay last' → :267`.

**Probe:** No unit spec imports this module (109 spec files grepped; jest bin absent — runner-blocked caveat stands). Deterministic probe from repo root:
`cd packages/nocodb && grep -c "name: '" src/helpers/getAstColumnStrategy.ts` → `12` and `grep -n 'defaultFieldStrategy,$' src/helpers/getAstColumnStrategy.ts` → last element of the array at :281.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "resolveColumnAst columnAstStrategies", limit: 10 });
```
Resolves `resolveColumnAst` :288-301 rank-1 total:1.

## Verdict
Adopt the ordered-chain pattern (order-as-priority, terminal catch-all, per-rung debug namespaces) and the exact rung semantics above; adapt strategy names/logging to host conventions; omit the EE query-client widening note unless porting the EE side. Coverage caveat: no direct tests at pin; probes are source-greps.
