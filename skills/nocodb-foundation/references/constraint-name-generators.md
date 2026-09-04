<!-- capsule-v2 -->
# constraint-name generators — why are FK and index names capped at 40 chars with a random tail?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What deterministic-plus-random scheme generates FK constraint names for links and index names for custom links, and what length budget must a port respect?

## constraint-name generators
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `randomID` (:39–42), `generateFkName` (:599–609), `generateIndexNameForCustomLink` (:612–624).
**Signature:** `generateFkName(parent: TableType, child: TableType) → \`fk_${p10}_${c10}_${randomID()}\``; same shape `idx_` prefixed for indexes.
**Data Shape:** nanoid custom alphabet `'1234567890abcdefghijklmnopqrstuvwxyz_'` (no uppercase, no zero, no hyphen), 10 chars; table/column stems `\W+→_` sanitized then sliced to 10.

### Decisive source
```ts
// :598–609 (comment verbatim):
// generate unique foreign key constraint name by taking first 10 chars of parent and child table name (by replacing all non word chars with _)
// and appending a random string of 15 chars maximum length.
// In database constraint name can be upto 64 chars and here we are generating a name of maximum 40 chars
const constraintName = `fk_${parent.table_name
  .replace(/\W+/g, '_')
  .slice(0, 10)}_${child.table_name
  .replace(/\W+/g, '_')
  .slice(0, 10)}_${randomID()}`;
```

**Flow:** sanitize both identifiers (non-word runs collapse to single `_`) → truncate each to 10 → join `fk_`/`idx_` + stem + stem + 10-char random id → ≤4+10+1+10+1+10 = 36–40 chars, safely inside every dialect's 64-char identifier limit including mm junction double-naming.
**Invariant:** The random tail is collision insurance across re-runs/rename cycles where identical stem pairs recur; the alphabet avoids case-folding and quoting hazards on case-insensitive engines. Stems come from PHYSICAL table_name (not titles). Ports that raise the slice past 10 break the documented 40-char ceiling comment.
**Probe:** `grep -c "_\${randomID()}" packages/nocodb/src/helpers/columnHelpers.ts` → `2` (both generators share the pattern; :607 fk, :621 idx).
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "generateFkName generateIndexNameForCustomLink", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 10+10+10 budget and sanitizing rule verbatim; adapt alphabet if host forbids `_`-leading ids. Companion: `getMMColumnNames` (:758–771) truncates junction FK columns to `${table_name.slice(0,30)}_id` with a self-ref disambiguator appending `1` at 29 chars — the same length-budget thinking at column scale (`grep -c "slice(0, 30)}_id" → 2`).
