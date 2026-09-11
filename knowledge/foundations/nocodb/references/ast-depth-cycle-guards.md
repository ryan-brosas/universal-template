<!-- capsule-v2 -->
# getAst nested-expansion guards — how deep can a client-driven AST request recurse before it must be truncated?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** `?nested[a][nested][b][nested]…` is client-controlled and LTAR/Lookup metadata can be cyclic — what exactly stops the recursion from blowing the stack or building self-referencing SQL?

## Depth cap on the AST walk + cycle guard on the dependency walk
**Path/Symbol:** `packages/nocodb/src/helpers/getAst.ts:getAst` (:36-368), `extractDependencies` (:452-492), `extractLookupDependencies` (:494-532).
**Signature:** `const getAst = async (context: NcContext, { query?, extractOnlyPrimaries?=false, includePkByDefault?=true, model, view?, dependencyFields? = {...query, nested:{...}, fieldsSet:new Set()}, getHiddenColumn?, throwErrorIfInvalidParams?=false, extractOnlyRangeFields?=false, apiVersion?=NcApiVersion.V2, extractOrderColumn?=false, includeSortAndFilterColumns?=false, includeRowColorColumns?=false, includeButtonFilterColumns?=false, skipSubstitutingColumnIds?=false, fk_display_value_column_id?, allowRequestedHiddenFields?=false, _depth = 0 }) => Promise<{ ast: Ast; dependencyFields; parsedQuery }>`
**Data Shape:** Returns `{ ast, dependencyFields, parsedQuery: dependencyFields }` where `ast` keys are column titles (or ids when `skipSubstitutingColumnIds`) mapping to `1 | true | null | Ast`; `dependencyFields.nested[title]` buckets are MUTATED in place and shared across recursion. 7 files import `~/helpers/getAst`.

### Decisive source
```ts
if (_depth > GET_AST_MAX_DEPTH) {
  logger.warn(
    `getAst recursion depth exceeded (${_depth} > ${GET_AST_MAX_DEPTH}) for model ${model.id}; ` +
      `truncating nested expansion. …`,
  );
  return { ast: {}, dependencyFields, parsedQuery: dependencyFields };
```
(:94-101 — `GET_AST_MAX_DEPTH = 8` at :34. Truncation returns an EMPTY ast `{}` for that subtree — the branch silently disappears from the response rather than erroring.)

**Flow:** depth check → per-column loop: nested-fields branch recurses into related tables via `getRelContext(context).refContext` (:273-284 / :327-340, each passing `_depth + 1`) → inclusion decided by `resolveColumnAst` strategy chain → dependencies collected via `extractDependencies`, which walks Lookup chains with a `_visited` Set cycle guard (:467-474) and adds physical column titles to `fieldsSet`.
**Invariant:** The AST walk and the DEPENDENCY walk are two separate recursions with two separate guards — a depth cap alone does not stop `extractDependencies` from looping forever on an A→B→A Lookup chain; only the `_visited` set does.

### Porting traps (each verified against source)
- **The `_visited` guard exists because of a production Knex infinite loop:** the comment pins "a SELECT QueryBuilder that contains itself — which is what trips the Knex `columnize → wrap → toSQL → unwrapRaw → wrap` infinite loop seen in production" (:461-465).
- **Lookup-dependency bucket normalization (:513-524):** the nested bucket for the relation column may have been seeded from the request query WITHOUT `nested`/`fieldsSet` (e.g. export's `buildNestedLinkLimitQuery` puts `{ limit }` objects under link titles) — both are normalized before use because "`extractDependencies` writes straight to `fieldsSet.add(...)` and, unlike `getAst`, never defaults it, so a missing set would crash." In-file anchor: `grep -n 'never defaults it' src/helpers/getAst.ts` → :518.
- **Broken relations degrade, never throw:** missing colOptions or missing related table → warn + `ast[colTitle] = null; continue` (:251-269/:304-324) so data retrieval continues.
- **In-file anchors:** `grep -n 'GET_AST_MAX_DEPTH = \|_depth > GET_AST_MAX_DEPTH\|already visited in this dependency walk' src/helpers/getAst.ts` → :34/:94/:470.

**Probe:** No unit spec imports this helper (109 spec files grepped; jest bin absent — runner-blocked caveat stands). Deterministic probe from repo root:
`cd packages/nocodb && grep -n '_depth > GET_AST_MAX_DEPTH' src/helpers/getAst.ts` → `94:` and `sed -n '461,474p' src/helpers/getAst.ts | grep -c '_visited.has'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getAst extractDependencies", limit: 10 });
```
Resolves `extractDependencies` :452-492 rank-1 and `getAst` :36-368 rank-2 (`has_more: true` — page for the rest).

## Verdict
Adopt the dual-guard shape (depth cap on AST recursion, visited-set on dependency cycles), empty-AST truncation semantics, and bucket normalization before fieldsSet.add; adapt the depth constant (8) to host needs; omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
