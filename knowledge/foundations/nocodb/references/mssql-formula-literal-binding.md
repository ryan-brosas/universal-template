<!-- capsule-v2 -->
# mssql formula literal binding — when must a string literal be inlined as N'...' instead of bound as a parameter?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** Why does the Literal node branch special-case mssql string and boolean literals, and what escaping keeps stray `?` characters from shifting bindings?

## mssql formula literal binding
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:_formulaQueryBuilder.fn` Literal branch (:411–435).
**Signature:** `(pt: {type:'Literal', value}) => { builder: Knex.Raw }`.
**Data Shape:** string literals → inline `N'<value>'` with `'` doubled and `?` escaped to `\?`; boolean literals → raw `1|0`; everything else (numbers, nulls, non-mssql) → normal `?` binding.

### Decisive source
```ts
// :411–435
} else if (pt.type === 'Literal') {
  if (knex.clientType() === 'mssql' && typeof pt.value === 'string') {
    return { builder: knex.raw(
      `N'${pt.value.replace(/'/g, "''").replace(/\?/g, '\\?')}'`) };
  }
  if (knex.clientType() === 'mssql' && typeof pt.value === 'boolean') {
    return { builder: knex.raw(pt.value ? '1' : '0') };
  }
  return { builder: knex.raw(`?`, [pt.value]) };
}
```

**Flow:** two mssql-specific reasons force inlining: (1) UNICODE — a bound string inlines through `.toQuery()` as plain varchar, losing nvarchar typing; `N'...'` preserves it. (2) BINDING LIFETIME — the single-query (dbQueryClient) path composes this builder into a LARGER statement resolved by ONE final `.toQuery()`; a bound `?` placeholder emitted here gets consumed/shifted by that outer compilation, so later bindings land in the wrong slots. Escaping any `?` INSIDE the value to `\?` keeps it a literal through the final unescape — without it, e.g. `CONCAT(x, '?')` shifts every subsequent binding and a pk value lands in the `TOP (…)` clause as `TOP ('1')` → SQL Server error 1060. Booleans are inlined as `1/0` because T-SQL has no boolean literal type. Lookup-of-formula re-escapes after its own `.toQuery()` so net escaping stays single (see mssql.ts mapping module).
**Invariant:** (1) Escape order matters: double quotes FIRST, then escape `?` — and the final `.toQuery()` is what turns `\?` back into a literal `?`; double-unescaping produces bare placeholders again. (2) This applies ONLY to mssql string literals; porting it to other clients breaks their parameterized caching. (3) The same `\?` re-escape doctrine exists at the binary/call exits (`sql.replace(/\?/g,'\\?')` before `knex.raw` in parsed-tree-builder :329/:720) — any new code path that materializes a builder to a string and re-wraps it must repeat it exactly once.
**Probe:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` :411–435. Runner BLOCKED (no upstream tests) → line-anchored deterministic check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "Literal N'' mssql boolean 1 0 knex.raw", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inline-N-literal + `\?` self-escaping for mssql string literals and 1/0 boolean literals; adapt to host drivers only where they share the single-final-toQuery composition; omit elsewhere (all other clients keep bound parameters).
