<!-- capsule-v2 -->
# Gantt links-as-LTAR duality — why must a shared flag reach BOTH the AST and the SQL list args?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When a shared view needs Links columns expanded into nested rows instead of counts, which two consumers must agree?

## PublicDatasService.dataList Gantt branch
**Path/Symbol:** `packages/nocodb/src/services/public-datas.service.ts:dataList` (:125-224), Gantt handling at :182-202.
**Signature:** `const isGanttShared = view.type === ViewTypes.GANTT;` then getAst receives `{linksAsLtar: 'true'}` while listArgs receive `listArgs.linksAsLtar = 'true'`.
**Data Shape:** One string flag, two destinations: `getAst({query: isGanttShared ? {linksAsLtar: 'true'} : {}})` shapes the AST; `listArgs.linksAsLtar = 'true'` shapes baseModel.list's SQL.

### Decisive source
```ts
// For Gantt shared views the dep-link Links column must expand into
// nested LTAR rows in BOTH the AST (which drives nocoExecute's
// response shape) and listArgs (which drives baseModel.list's SQL).
// Setting it on listArgs alone fetches the nested data but then
// nocoExecute strips it because the AST still says
// `Predecessor: 1` (count form).
const isGanttShared = view.type === ViewTypes.GANTT;
const { ast, dependencyFields } = await getAst(context, {
  model,
  query: isGanttShared ? { linksAsLtar: 'true' } : {},
  view,
  includeRowColorColumns: query.include_row_color === 'true',
});
...
// baseModel.list also reads linksAsLtar — see getAst note above.
if (isGanttShared) { listArgs.linksAsLtar = 'true'; }
```

**Flow:** type-gated per shared route (dataList accepts GRID/KANBAN/GALLERY/MAP/CALENDAR/TIMELINE/GANTT but NOT FORM) → password → restrictSharedViewQuery → getAst with/without the flag → listArgs spread `{...query, ...dependencyFields}` + JSON-parsed filterArr/sortArr → conditional flag re-application AFTER the spread (a caller-supplied `query.linksAsLtar` cannot enable it for non-Gantt views because the query spread happens first and the flag is only SET, never read from query) → nocoExecute(ast, baseModel.list(listArgs)) → count → PagedResponse.
**Invariant:** Response shape lives in TWO places that must be flipped TOGETHER: fetch shape (SQL nesting) and projection shape (AST). Flipping one yields silent wrongness — data fetched but stripped (`Predecessor: 1`) or AST promising rows the query never selected. Error funnel: NcError/NcBaseError rethrow, everything else logs + generic internalServerError so stack traces never reach anonymous callers.
**Probe:** No runner at this pin — deterministic probe: grep confirms exactly one `linksAsLtar` pair of assignments (:186/:201) and one comment block explaining the dual consumer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "linksAsLtar gantt shared", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-destination feature flags wherever an execution layer and a projection layer both encode shape. Adapt the flag name/type to host. Omit if your AST and query builder are one structure.
