<!-- capsule-v2 -->
# virtual column title dedup — how are duplicate hm/bt titles disambiguated during meta population without a DB round-trip?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When two relations would produce the same virtual column title, what naming ladder applies and why can't getUniqueColumnAliasName be reused here?

## virtual column title dedup
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — inside `virtualColumnsInsert` closure (:484–562; counter loop :486–494).
**Signature:** `while (\`${column.title}${c || ''}\` in columnNames) c++; column.title = \`${column.title}${c || ''}\`;`.
**Data Shape:** local `columnNames` map seeded empty per TABLE (not per model) — tracks titles already consumed in this wave.

### Decisive source
```ts
// :484–493:
const columnNames = {};
for (const column of virtualColumns) {
  // generate unique name if there is any duplicate column name
  let c = 0;
  while (`${column.title}${c || ''}` in columnNames) {
    c++;
  }
  column.title = `${column.title}${c || ''}`;
  columnNames[column.title] = true;
```

**Flow:** first occurrence keeps bare title (`c=0` renders as empty suffix via `c || ''`) → second gets `Title1`, third `Title2` … → each claimed title is registered before the next candidate is tested.
**Invariant:** The suffix scheme is `''`, `1`, `2`… with NO separator, and `0` is never emitted because of the `c || ''` coercion. This differs from `getUniqueColumnAliasName`/`getColumnNameAlias` helpers used elsewhere in the same file for REAL columns — those consult existing model columns from DB state, whereas this loop only knows titles minted within the current deferred batch (real columns were inserted in the previous wave and are not consulted). Porters who swap in the shared helper change collision behavior across waves.
**Probe:** `grep -c "columnNames[column.title] = true" packages/nocodb/src/helpers/populateMeta.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "populateMeta virtualColumnsInsert title", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the zero-based suffix ladder and per-batch scope exactly; adapt error handling around the insert (the try/catch at :556–558 logs-and-continues per relation so one broken FK doesn't abort sibling links).
