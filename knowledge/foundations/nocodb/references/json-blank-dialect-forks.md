<!-- capsule-v2 -->
# JSON blank semantics — how does "blank" mean NULL ∪ {} ∪ [] per dialect, and why do pg/mysql diverge on eq?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do JSON handlers define empty across engines, and what breaks if you reuse the generic text ops?

## JsonGeneralHandler + Pg/MySql twins
**Path/Symbol:** `json/json.general.handler.ts` — fieldExpr hook :25; filter :29+; parseJsonValue :176+; NC_MAX_TEXT_LENGTH gate :214-224. `json.pg.handler.ts` appendIsNull/appendIsNotNull :13-35 + ::jsonb/::text forks. `json.mysql.handler.ts` JSON_UNQUOTE variants.
**Signature:** `protected fieldExpr(_column?: Column): string` — default `'??'`; the documented override point ("SQL Server's native `json` ... override this to wrap the field in an explicit cast"; receives column so a dialect can cast only native json, not nvarchar-typed).
**Data Shape:** blank = `IS NULL OR field='{}' OR field='[]'` (general), pg adds `::text = ''`, mysql wraps JSON_UNQUOTE around every comparison.

### Decisive source
```ts
// json.general.handler.ts :31-41 — the extension contract:
// Default is the bare quoted identifier (`??`). Dialects whose JSON type
// forbids implicit string comparison (e.g. SQL Server's native `json`, which
// behaves like `xml`) override this to wrap the field in an explicit cast.
// ... Receives the column so a dialect can decide per underlying type.
// json.pg.handler.ts eq fork:
qb.where(knex.raw('??::jsonb = ?::jsonb', [field, jsonVal]));  // valid JSON → semantic equality
qb.where(knex.raw('??::text = ?', [field, jsonVal]));          // non-JSON → textual equality
```

**Flow:** eq/neq parse the value via parseJsonValue ({object→JSON.stringify} | {string→try JSON.parse}) → valid rides the engine's JSON equality (pg ::jsonb; mysql JSON_UNQUOTE =) else falls to TEXT equality → negations add orWhereNull → like/nlike operate on text projections (::text ilike on PG; JSON_UNQUOTE like on MySQL) → is/isnot keyword-map onto the same appendIsNull/appendIsNotNull pair → unsupported ops throw.
**Invariant:** (1) PG's dual-cast fork IS semantic: jsonb equality normalizes key order/whitespace, text equality doesn't — picking one for both cases corrupts one class of filters. (2) The MySQL neq arm keys its null-guard on `val === ''` while general/pg use ncIsStringHasValue — a deliberate narrower check (only '' triggers notnull-only). (3) parseUserInput enforces NC_MAX_TEXT_LENGTH BEFORE validity so oversized junk fails with the length error, not a parse error.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "::jsonb = ?::jsonb" in json.pg.handler.ts; search_graph resolves `JsonPgHandler.filter Method` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JsonPgHandler", limit: 5 });
```

## Verdict
Adopt the three-tier blank definition and dual-cast equality; adapt function names per engine; omit mssql/oracle shells (inherit general unchanged at this pin). Caveat: no direct tests at pin.
