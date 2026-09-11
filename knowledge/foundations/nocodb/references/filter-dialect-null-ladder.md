<!-- capsule-v2 -->
# conditionV2 dialect ladder — which comparison ops carry hidden NULL-membership arms, MySQL BINARY, and Oracle ''≡NULL corrections?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When porting the generic (non-FieldHandler) comparison switch, which per-dialect and NULL-semantics corrections does each operator silently depend on?

## Generic comparison switch
**Path/Symbol:** `packages/nocodb/src/db/conditionV2.ts:parseConditionV2` clause builder (:436-883).
**Signature:** `clause: (qb: Knex.QueryBuilder) => void` closing over `_field/_val/column`; numeric-coerces string values for `isNumericCol(uidt)` (:446-452); Formula operands SWAP `[field, val] = [val, field]` because the compiled expression is the subject.
**Data Shape:** Reaches this switch only for uidts NOT in the FieldHandler early-route list (:340-368) — plain strings/Checkbox/etc. plus Rollup/Links WITH customWhereClause.

### Decisive source
```ts
// eq :477-479 — MySQL compares strings case-INSENSITIVELY by default;
// BINARY restores case-sensitive equality for plain columns only
qb = qb.where(knex.raw('BINARY ?? = ?', [field, val]));

// neq/not :505-523 — the classic trap: NOT-equal must ALSO surface NULLs,
// else rows with NULL silently vanish from "not equal" results
nestedQb.where(knex.raw('BINARY ?? != ?', [field, val]));
nestedQb.orWhereNull(customWhereClause ? _val : _field);   // ← every dialect

// nlike :621-628 — negated-like keeps empty/null visible, but ONLY null
// when the pattern is degenerate '%%'
if (val !== '%%') { nestedQb.orWhere(field, ''); nestedQb.orWhereNull(field); }
else              { nestedQb.orWhereNull(field); }

// notempty :757-767 — Oracle stores '' as NULL; `<> '' OR IS NULL` would
// match only NULL rows (`field <> NULL` is never true). Match EVERY row.
if (knex.clientType() === 'oracledb') { qb = qb.whereRaw('1 = 1'); break; }

// blank :806-821 — empty-string arm is skipped for numerics, date family,
// AND all of Oracle ('' ≡ NULL makes it unreachable there)
qb = qb.whereNull(customWhereClause || field);
if (!isNumericCol(column.uidt) && !dateFamily.includes(column.uidt)
    && knex.clientType() !== 'oracledb') qb = qb.orWhere(field, '');

// like + Formula :551-559 — swap then de-quote an already-wrapped pattern
[field, val] = [val, field];
val = `%${val}%`.replace(/^%'([\s\S]*)'%$/, '%$1%');
```

**Flow:** value prep (empty/notempty ⇒ `''`, current-user substitution) → numeric coercion → per-op SQL: eq/neq (MySQL BINARY + OR-NULL), like/nlike (pg `::text ilike`, Oracle `UPPER(UPPER)` pair, dynamic-ref pattern concat via `ncLikePatternForRef`), allof/anyof/nallof/nanyof (CSV membership via wrapped `,field,` LIKE pairs — pg ilike / sqlite like / mssql NVARCHAR+concat / MySQL CONCAT; enum/set values get `trimEnd()`; negated forms wrap whereNot + orWhereNull), gt/ge/lt/le INVERT under customWhereClause (:701-712 `<` means user-gt when roles swapped), in → whereIn CSV split, is/isnot keyword ladder (null/notnull/empty/notempty/true/false), btw/nbtw via `extractArray` guard (array passthrough vs `'a,b'`.split), checked/notchecked.
**Invariant:** (1) Every negation op (neq/not/nlike/notblank/notchecked/nanyof-family) MUST re-admit NULL (and usually '') or filtered sets silently shrink. (2) Oracle: no boolean literal pre-23ai → use `1 = 1`; CLOB operands narrowed before equality/ordering. (3) customWhereClause flips field/value roles INCLUDING comparison direction. (4) Formula operand swap happens BEFORE wildcard wrapping.
**Probe:** No unit tests upstream. Deterministic probe: `neq x` on a column with a NULL row must render `(col != x OR col IS NULL)` on every dialect; `nlike %%` renders `NOT like '%%' OR col IS NULL` WITHOUT the empty-string arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "conditionV2 clause neq orWhereNull", limit: 5 });
// nocodb.packages.nocodb.src.db.conditionV2.parseConditionV2 Function conditionV2.ts 145-886
```

## Verdict
Adopt the negation-re-admits-NULL rule, MySQL BINARY eq for case-sensitive text, Oracle ''≡NULL branches (`1=1` notempty, no empty-string arm in blank), and the CWC direction inversion. Adapt the exact dialect raw-SQL strings to your query layer. Caveat: no direct tests at pin; ranges verified against graph.
