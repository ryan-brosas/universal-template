<!-- capsule-v2 -->
# LongText AI-prompt projection + case rules — how does a text column filter the `.value` of stored JSON, and where do PG/MySQL flip case sensitivity?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do LongText/Email/URL/PhoneNumber/SingleLineText share one handler family while per-dialect LIKE/BINARY rules stay correct?

## LongTextGeneralHandler + Pg/Mysql variants + text-family subclasses
**Path/Symbol:** `long-text/long-text.general.handler.ts` — getFieldExpression :24-60; filter override :69-91; applySort :94+; parseUserInput :112-157 with the NC_MAX_TEXT_LENGTH gate :147-155. `long-text.pg.handler.ts` (:16-26) delegates like/nlike to GenericPgFieldHandler (ILIKE). `long-text.mysql.handler.ts` — filterEq/filterNeq emit `BINARY ?? = ?` / `!= ?` (:20-47). Subclasses `email`, `phone-number`, `single-line-text` = empty `extends LongTextGeneralHandler` (registry `field-handler/index.ts`: SingleLineText CLIENT_DEFAULT :128, LongText PG :132).
**Signature:** `getFieldExpression(knex, column, alias?): string | Knex.Raw` — plain columns return the raw ref; `isAIPromptCol(column)` returns per-dialect extraction: pg `TRIM('"' FROM (col::jsonb->>'value'))`, mysql `JSON_UNQUOTE(JSON_EXTRACT(col,'$.value'))`, sqlite `json_extract(col,'$.value')`, mssql+oracle `JSON_VALUE(col,'$.value')`.
**Data Shape:** getFieldExpression returns either the bare `alias.column_name` ref (plain columns) or a dialect-specific `Knex.Raw` extracting `.value`; AI-prompt detection rides nocodb-sdk's `isAIPromptCol`. parseUserInput unwraps `{value}` objects ONLY for AI cols, stringifies everything else via `value?.toString() ?? ''`, throws `valueLengthExceedLimit` past NC_MAX_TEXT_LENGTH (:147), then returns `{ value: params.value }` — the ORIGINAL input object preserved for AI columns, the stringified form for plain ones.

### Decisive source
```ts
// long-text.pg.handler.ts :6-14 — why the delegation exists:
// On Postgres `LIKE` is case-sensitive, whereas every other supported
// dialect's `LIKE` ... is case-insensitive. LongText routes through
// FieldHandler, so without a PG-specific handler it inherits
// GenericFieldHandler's plain `LIKE` and the filter becomes case-sensitive.
// long-text.mysql.handler.ts :9-13:
// Without `BINARY`, MySQL's default case-insensitive collation would match
// `'ABC' = 'abc'` — the legacy switch in conditionV2 added this for all
// string columns.
```

**Flow:** non-AI columns fall through to generic behavior untouched; AI-prompt columns rewrite BOTH filter LHS and sort key to the extracted `.value` string → parseUserInput unwraps `{value}` objects, stringifies everything, enforces NC_MAX_TEXT_LENGTH, returns raw value for AI columns but string for plain ones → PG flips contains-matching to ILIKE via delegation; MySQL pins eq/neq to BINARY for parity with legacy conditionV2.
**Invariant:** (1) The mssql/oracle JSON_VALUE arms exist ONLY to match the unquoted scalar shape other engines produce — swapping JSON_QUERY would wrap results in brackets and break equality filters. (2) SingleLineText/Email/Phone inherit LongText so they ALSO get PG-ILIKE + MySQL-BINARY automatically — the family split is deliberate, not accidental duplication. (3) parseUserInput returning `params.value` (unstringified) for AI columns preserves the object payload for downstream writers.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "case-sensitive on PG" (:11); search_graph resolves `LongTextPgHandler Class` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "isAIPromptCol", limit: 5 });
```

## Verdict
Adopt the field-expression hook + family inheritance + two dialect case corrections; adapt extraction SQL; omit nothing. Caveat: no direct tests at pin.
