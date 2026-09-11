<!-- capsule-v2 -->
# Content wire-brand remap plane — how does a generic content API keep user-authored SQL taint-branded per dialect across the wire boundary?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** One content endpoint stores SQL snippets, log-SQL snippets, and notebooks under a single opaque `content` map with a plain `sql` field — how does the frontend make that user SQL unexecutable-by-accident (per dialect brand) without scattering casts across every query/mutation call site?

## The single-boundary sql↔unchecked_sql rename (`data/content/content-remap.ts`)
**Path/Symbol:** `apps/studio/data/content/content-remap.ts` : `remapSqlContentField` (:28-42), `remapSqlContentFields` (:44-46), `remapWireSnippet` (:54-57), `unmapSqlContentField` (:60-84).
**Signature:** `remapSqlContentField<T extends { type: string }>(item: T): T`; `unmapSqlContentField<T extends { type: string }>(item: T): T`.
**Data Shape:** the API stores/returns the field as `sql`; the frontend domain uses `unchecked_sql` branded PER TYPE — `type: 'sql'` ⇒ `untrustedSql(sql)` (Postgres brand from pg-meta), `type: 'log_sql'` ⇒ `untrustedLogSql(sql)` (analytics brand, pass-3 disjoint family), `type: 'notebook'` ⇒ `notebookDomainSchema.parse(content)` (per-cell branding via the pass-3 notebook wire/domain transform); non-SQL types pass through by REFERENCE identity (`return item`, not a copy). Branding is per-type and "never mixed" — a Postgres snippet can never carry the logs brand or vice versa.

### Decisive source
```ts
const { sql, ...rest } = content
const unchecked_sql =
  item.type === 'log_sql' ? untrustedLogSql(sql as string) : untrustedSql(sql as string)
return { ...item, content: { ...rest, unchecked_sql } } as T
```

**Flow:** every FETCH path runs rows through remapSqlContentFields at the boundary; every SAVE path runs items through unmapSqlContentField before the request. `remapWireSnippet(row, status)` concentrates the single `as unknown as` assertion (the platform API types `content` as an opaque `{ [key: string]: unknown }` map) in the one place that already owns the rename, so query/mutation call sites stay cast-free.
**Invariant:** the taint brand is assigned at EXACTLY ONE boundary, keyed on the content's type discriminator — any call site that brands (or debrands) independently can drift from the wire shape. Round-trip remap∘unmap must be identity.
**Probe:** `content-remap.test.ts` (313L, read whole): per-type branding pins (sql→untrustedSql, log_sql→untrustedLogSql, notebook per-cell with markdown untouched), "leaves non-SQL content types unchanged" by reference identity, round-trip identity for both snippet types. Vitest unexecutable in-lane — never claimed passing.

## Never fabricate sql: undefined (`unmapSqlContentField`)
**Path/Symbol:** `content-remap.ts` : missing-field guard (:69-81).
**Signature:** n/a — failure-mode contract of the reverse remap.
**Data Shape:** a payload MISSING `unchecked_sql` is a NO-OP — the in-source comment: "Crucially, we NEVER fabricate `sql: undefined` here: that would clobber the user's saved query text." If a raw `sql` field is still present (a save path missed during the rename), development throws loudly ("a save path was not migrated to the branded field") while production silently passes the pre-rename shape through — which happens to already be the correct wire shape.

### Decisive source
```ts
if (!('unchecked_sql' in content)) {
  // Defensive guard against a writer that still submits the pre-rename `{ sql }` shape.
  // Such a payload happens to reach the wire correctly (the API stores `sql`), but it
  // means a save path was missed during the rename — surface it loudly in development.
  // Crucially, we NEVER fabricate `sql: undefined` here: that would clobber the user's
  // saved query text. The no-op below preserves whatever the content already holds.
  if (process.env.NODE_ENV !== 'production' && 'sql' in content) {
    throw new Error(
      `unmapSqlContentField: ${item.type} content is missing 'unchecked_sql' but still carries a raw 'sql' field — a save path was not migrated to the branded field.`
    )
  }
  return item
}
```

**Flow:** save path → unmap → if unchecked_sql present, swap it back to sql; if absent, preserve whatever is there (dev-only loud throw when a raw sql coexists).
**Invariant:** a serializer must never emit an explicit undefined for a field the backend treats as "overwrite" — absence means "leave as-is", and a dev-only loud failure is the right alarm for a missed migration because the pre-rename shape is accidentally wire-correct.
**Probe:** test pins "leaves content without a sql or unchecked_sql field unchanged (never fabricates sql)", "throws in development when content still carries a raw sql field (missed rename)", and "never clobbers a raw sql field in production (defensive no-op)" (NODE_ENV stubbed).

## Server-issued cursor pagination + typed fetch variants (`content-infinite-query.ts`, `content-id-query.ts`)
**Path/Symbol:** `apps/studio/data/content/content-infinite-query.ts` : `getContent` (:18-48), `useContentInfiniteQuery` (:53-75); `content-id-query.ts` : `getContentById` (:18-34), `getSqlSnippetById` (:43-57); `keys.ts` : `contentKeys` (:2-46).
**Signature:** `getNextPageParam: (lastPage) => lastPage.cursor` — the cursor is a SERVER-ISSUED opaque string.
**Data Shape:** the third pagination variant in this foundation (vs pass-3's client-composed keyset tuple filter and pass-4's composite keyset over UNION ALL): the client never constructs the cursor, only echoes it back as a query param; limit defaults to 10; every page's rows pass through `remapSqlContentFields` at the fetch boundary. Id lookups come in two typed flavors: generic `getContentById` (remaps, returns Content['content']) and editor-specific `getSqlSnippetById` which returns a `SnippetWithContent` (status 'saved') "ready to drop into the store — no narrowing/casting at the call site". Error handling differs by fatality: list fetches call `handleError(error)` non-throwing (degrade), id lookups `throw handleError(error)` (fatal). Keys root at `['projects', projectRef, ...]` with `.filter(Boolean)` option members (the pass-4 database-queues deviation pattern).

### Decisive source
```ts
export const useContentInfiniteQuery = <TData = ContentData>(...) => {
  return useInfiniteQuery({
    queryKey: contentKeys.infiniteList(projectRef, { type, name, limit, sort }),
    queryFn: ({ signal, pageParam }) =>
      getContent({ projectRef, type, name, limit, sort, cursor: pageParam }, signal),
    enabled: enabled && typeof projectRef !== 'undefined',
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.cursor,
    ...options,
  })
}
```

**Flow:** list page N+1 = server cursor from page N → GET /content?type&name&sort_by&limit&cursor → remap fields → append; detail = GET /content/item/{id} → remapWireSnippet/getContentById → cache under contentKeys.resource.
**Invariant:** when the server owns ordering state (filters, favorites, visibility), the cursor must stay OPAQUE to the client — constructing it client-side couples pagination to server internals; and the brand remap belongs at the fetch boundary so cached data is already domain-shaped.
**Probe:** direct read at the pin; no dedicated test for the two query modules (they compose the tested remap + pass-1 fetchers — recorded as consumer-only); `content-remap.test.ts` covers the boundary they depend on.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "remapSqlContentField unmapSqlContentField remapWireSnippet getNextPageParam contentKeys", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the single-boundary type-keyed brand assignment (wire field name ↔ domain branded field) with reference-identity passthrough for non-applicable types; the never-fabricate-undefined reverse-remap with dev-only loud throw for missed migrations; concentrated single-assertion helpers so call sites stay cast-free; opaque server-issued cursors echoed verbatim; and fatal-vs-degrading error handling split between id lookups and lists. Adapt the field names, type discriminators, and brand functions to your dialect set. Omit Supabase-product specifics: the platform endpoint paths and the SnippetWithContent store shape. Direct-test caveat: content-remap.test.ts (313L) read whole; query modules are consumer-only (no dedicated tests); vitest unexecutable in-lane — never claimed passing.
