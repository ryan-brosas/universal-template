<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :166–167 (`abstract concat/simpleCast`) + dialect bodies pg.ts:16–22, mysql.ts:20–26, sqlite.ts:15–19 — the abstract-pair contract.

# Question
Which two string-SQL primitives MUST every new dialect client implement, and what breaks if one is missing?

## Path / Symbol
`concat(fields: string[])`, `simpleCast(field, asType)` — the only ABSTRACT members of GenericDBQueryClient besides bulkAggregateRowSelector.

## Data Shape
concat joins field EXPRESSIONS (already SQL text) with the dialect's operator/function; simpleCast emits a cast of an expression to a TYPE KEYWORD.

## Decisive source
generic.ts:166–167 — declared abstract, so TypeScript enforces implementation at subclass-writing time; mssql/oracle EE stubs throw instead of implementing (:18–24 both files), keeping the compile contract while failing at runtime.
Dialect matrix: pg `CONCAT(a, b)` + `x::type`; mysql same CONCAT + CAST(x AS CHAR-for-TEXT) (:24 maps TEXT→CHAR because MySQL has no TEXT cast target in expressions); sqlite `a || b` + plain CAST.
Consumers live in formula/lookup compilation (formulav2 + generateLookupSelectQuery import DBQueryClient for exactly these two) — e.g. string-cast formula re-dispatch uses simpleCast('expr','CHAR') on mysql.
Type-keyword portability is the trap: 'TEXT' is valid pg/sqlite but must translate to CHAR on MySQL — hence the translation INSIDE the client rather than at call sites.

## Flow / Invariant
Porter rule: call sites speak STANDARD type vocabulary (TEXT); clients translate to engine keywords. Adding a dialect without these two methods fails compilation (good); adding one whose cast map lacks TEXT silently produces `CAST(x as TEXT)` on engines where that's not parseable — extend the keyword map, never bypass the client.

## Probe (direct test)
From repo root:
```
grep -c 'abstract concat\|abstract simpleCast' packages/nocodb/src/dbQueryClient/generic.ts   # => 2 (:166,:167)
grep -n 'TEXT' packages/nocodb/src/dbQueryClient/mysql.ts                                     # => 1 (:24)
grep -n "join(' || ')" packages/nocodb/src/dbQueryClient/sqlite.ts | head -1                  # => :16
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"simpleCast concat","limit":4,"detail":"compact"}'
```
→ resolves all five implementations line-exact.

## Verdict
**Adapt.** Port the pair as a required interface with per-engine keyword maps; keep standard vocabularies at call sites.
