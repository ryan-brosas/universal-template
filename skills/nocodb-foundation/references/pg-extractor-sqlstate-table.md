<!-- capsule-v2 -->
# pg error code table — which SQLSTATEs become friendly 422s, and why does the extractor deliberately return undefined for internal errors?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the PG extractor turn `error.detail`/`error.hint` into user-safe messages WITHOUT leaking backend internals — and where does it choose silence over a message?

## SQLSTATE ladder with detail-parsing + deliberate XX000 blackhole

**Path/Symbol:** `packages/nocodb/src/helpers/db-error/pg.extractor.ts:PgDBErrorExtractor.extract` (:44–393), `pgRawMessage` (:18–35), unique-violation detail parser (:64–123), not-null column fallback (:128–146), FK branch (:147–170), check-constraint hint branch (:171–189), PL/pgSQL P0001–P0004 (:190–200), XX000 return-undefined (:358–375).
**Signature:** `extract(error: any): DBErrorExtractResult` — returns `{ error: NcErrorType.ERR_DATABASE_OP_FAILED, message, code: error.code, httpStatus, details? }`; httpStatus defaults 422.
**Data Shape:** `_extra` becomes `details` (column / value / constraint / table / dataType / token); `_type` (DBError enum) is computed but NOT included in the result — only the SDK error type + message + code + status ship.

### Decisive source
```ts
// :64-93 — unique violation: parse "Key ("Text_7")=(a) already exists."
case '23505': {
  message = 'This record already exists.';
  _type = DBError.UNIQUE_CONSTRAINT_VIOLATION;
  const columnNameMatch = errorDetail.match(/Key\s*\(([^)]+)\)\s*=/);
  columnName = columnNameMatch[1].split(',')[0].trim().replace(/^["']|["']$/g, '');
  ...
  message = `${columnName} field unique constraint violation. Value '${duplicateValue}' already exists.`;
```

**Flow:** switch on `error.code` → constraint codes parse PG `detail`/`hint`: 23505 extracts first column of composite keys (`split(',')[0]`) and the duplicate value; 23502 takes `error.column` with regex fallback `/null value in column "([^"]+)"/i`, exposing `details.column` so downstream formatters can append "(column: X)"; 23503 strips the physical table reference from detail via `/\s*(?:in|from) table\s+"[^"]+"\.?/i` and splits "is not present" (insert) vs "is still referenced" (delete) phrasing; 23514 prefers the schema author's RAISE-style `hint`; P0001–P0004 surface user-authored PL/pgSQL messages joined with any hint by " — ". Type/value mismatches (22P02/22003) try two regex candidates then fall back to detail/` set "col"` parsing. Status overrides: 28000→401, 40001→409, EACCES→403, 53300→503, 40P01→500, unknown→500. **XX000 is handled by RETURNING UNDEFINED after logging** — the comment pins that `error.message` often contains backend internals we don't want on end-user toasts, and that triage callers fall back to raw text themselves.
**Invariant:** (1) Every user-visible string is either a fixed template or built from parsed PG fields — raw `error.message` reaches users only for check violations' fallback and never for XX000. (2) The 23505 note pins division of labor: if `handleUniqueConstraintError` ran first, this extractor sees only leftovers; its generic message is the FALLBACK, not the primary UX. (3) `default:` logs `${code} is not handled on database pg` and RETURNS the generic 500 — unhandled ≠ silent; only XX000 is silent-by-design.

### Porting traps (each verified against source)
- `pgRawMessage` strips Knex's `<sql> - <msg>` prefix using a SQL-verb anchor and the FIRST ` - ` separator so a user RAISE EXCEPTION containing ` - ` survives intact (:23–34).
- 42P07/42P01/42701/42703 extract table/column names from message shapes like `relation "?" already exists` — quoted-or-bare variants differ per case; port them verbatim (:224–337).
- In-file anchors: `grep -c "case '23505'" src/helpers/db-error/pg.extractor.ts` → 1; `grep -c "case 'P0001'" …` → 1; `grep -c 'XX000' …` → 2 (comment + log line); `grep -c 'is still referenced' …` → 1; `grep -c 'httpStatus = 503' …` → 1.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n "case 'XX000'" src/helpers/db-error/pg.extractor.ts | cut -d: -f1` → `358` and `sed -n '372,376p' src/helpers/db-error/pg.extractor.ts | grep -c 'return;'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "PgDBErrorExtractor extract 23505 XX000", limit: 10 });
```
Resolves `PgDBErrorExtractor.extract` :44-393 rank-1.

## Verdict
Adopt the SQLSTATE→(message template, httpStatus) table shape, detail/hint parsing with physical-name stripping, and the XX000 return-undefined leak-guard; adapt messages/i18n to host; omit NestJS logger specifics. Coverage caveat: no direct tests at pin; probes are source-greps.
