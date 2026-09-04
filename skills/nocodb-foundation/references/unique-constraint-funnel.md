<!-- capsule-v2 -->
# unique-constraint funnel — how does a bare 23505 become "Value 'a' already exists" on the form's own field label, even when wrapper layers strip the driver code?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Callers use unique indexes as concurrency primitives (insert-and-treat-collision-as-done) AND as validation UX — one function must serve both without ever missing a violation, so what is the full detection + column-resolution ladder?

## 1,044-line paranoia funnel: detect-anywhere → resolve column → resolve label → ALWAYS throw

**Path/Symbol:** `packages/nocodb/src/helpers/uniqueConstraintErrorHandler.ts:isUniqueViolation` (:22–33), `extractColumnNameFromError` (:41–129), `findDuplicateColumnByQuery` (:139–187), `handleUniqueConstraintError` (:205–1044).
**Signature:** `handleUniqueConstraintError({error, baseModel, insertData?}): Promise<void>` — throws `UniqueConstraintViolationError({value, fieldName})` or does nothing; `isUniqueViolation(e): boolean` is the cheap sibling for idempotent-write callers.
**Data Shape:** Thrown error carries ONLY `{value, fieldName}` (SDK class); fieldName prefers form-view custom labels, falls to column title, then column_name, then `'unknown'`.

### Decisive source
```ts
// :221-262 — the ULTRA-EARLY check: stringify the whole error and search it
const has23505Anywhere =
  error?.code === '23505' || error?.code === 23505 ||
  error?.original?.code === 23505 || error?.nativeError?.code === 23505 ||
  String(error?.code) === '23505' || ... || error?.errno === 23505 ||
  // Deep check: recursively search for '23505' in the error object
  errorString.includes('23505');
// :264 comment: If we detect 23505, we MUST throw - no exceptions
```

**Flow:** DETECT — code/errno checks at every nesting level (error / original / nativeError), string AND number forms, extractor-processed shape (`error.error === 'ERR_DATABASE_OP_FAILED'`), MSSQL tedious numbers 2601/2627 on EREQUEST, Oracle ORA-00001 (+ legacy `errorNum: 1`), MySQL ER_DUP_ENTRY, SQLITE_CONSTRAINT+UNIQUE-message, plus JSON.stringify deep-search as last resort; RESOLVE COLUMN — (a) PG detail regex `Key\s*\(([^)]+)\)\s*=` with quote-stripping and composite-first-column split → match against model columns case-insensitively, (b) else first payload-backed unique column, (c) else LIVE DB PROBE `findDuplicateColumnByQuery` walking each unique column (value from payload by column_name OR title, soft-delete filter via deletedColValue whereNull/orWhere), (d) else first unique column; RESOLVE LABEL — if viewId is a FORM view, `FormViewColumn.list(context, viewId)` matched by fk_column_id (NOT View.getColumn, which expects a different id — pinned in-comment) supplies the custom label; THROW always. The file contains THREE near-duplicate detection blocks (:221–262 ultra-early, :436–451 definite, :520–573 ultimate) — deliberate redundancy whose comments state the failure mode they fear ("if this fails, nothing will work").
**Invariant:** (1) Missed detection converts an idempotent no-op into a thrown generic error (isUniqueViolation's doc comment pins this) — false negatives are the bug class this file exists to prevent; false positives just over-report. (2) The message-matching fallback in isUniqueViolation (`/unique|duplicate/i`) is intentional because "wrapper layers sometimes lose the driver code". (3) Every resolution failure still ends in UniqueConstraintViolationError with 'unknown' — the funnel never falls through to the raw error.

### Porting traps (each verified against source)
- extractColumnNameFromError tries FOUR sources for the message (`message || sqlMessage || detail || original.message/detail`) and FOUR dialect grammars (PG Key-pattern, Oracle 23ai `violated on table S.T columns (COL)`, constraint-name suffix `_key/_unique`, MySQL `for key 'x'` with PRIMARY/table-qualified variants, SQLite `UNIQUE constraint failed:`) — order matters because PG's Key regex would also match fragments of other dialects' details.
- The live-DB probe excludes soft-deleted rows so a duplicate against a trashed record doesn't misname the offending field (:162–171).
- In-file anchors: `grep -c "code === '23505'" src/helpers/uniqueConstraintErrorHandler.ts` → 17; `grep -c 'findDuplicateColumnByQuery' …` → 3 (decl + 2 call sites); `grep -c 'fk_column_id === column.id' …` → 1.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'ULTRA-EARLY CHECK' src/helpers/uniqueConstraintErrorHandler.ts | cut -d: -f1` → `221` and `sed -n '245,262p' src/helpers/uniqueConstraintErrorHandler.ts | grep -c "includes('23505')"` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "handleUniqueConstraintError UniqueConstraintViolationError 23505", limit: 10 });
```
Resolves `handleUniqueConstraintError` :205-1044 rank-1 and SDK `UniqueConstraintViolationError` :66-76 rank-2 (`has_more: false`).

## Verdict
Adopt the detection-anywhere doctrine (stringified deep search as backstop), the four-step column-resolution ladder, and the form-label final step; adapt to host ORM's error shapes keeping ALL nesting levels; omit the duplicated-block redundancy only if your language has algebraic error matching that makes it unnecessary. Coverage caveat: no direct tests at pin; probes are source-greps.
