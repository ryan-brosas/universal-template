<!-- capsule-v2 -->
# Public query key-blocklist — why are only TWO query keys deleted for shared views, and what must column-references use instead?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** A caller-controlled `nested` or `getHiddenColumn` leaks every column — where is the line between "delete the key" and "strip per term"?

## Two-key delete vs per-leaf strip doctrine
**Path/Symbol:** `packages/nocodb/src/helpers/publicQuerySanitizer.ts:sanitizePublicQuery` (whole 21L); applied at `services/public-datas.service.ts` (:79 import, :429, :918 call sites) + calendar-datas; complementary `restrictSharedViewQuery`/`restrictSharedViewColumnReferences` in helpers/sharedViewQueryHelpers.ts.
**Signature:** `sanitizePublicQuery<T extends Record<string, any>>(query: T): T`; PUBLIC_QUERY_BLOCKED_KEYS = ['getHiddenColumn', 'nested'] as const.
**Data Shape:** shallow copy with blocked keys deleted; never mutates input.

### Decisive source
```ts
// Only these two. Column REFERENCES in `where` / `sort` / `filterArrJson` /
// group-by are confined separately, by `restrictSharedViewQuery` and
// `restrictSharedViewColumnReferences` — they strip per leaf/term rather than
// deleting the key, so a multi-field search degrades instead of returning
// everything. See the DESIGN NOTE in public-datas.service.ts.
export const PUBLIC_QUERY_BLOCKED_KEYS = ['getHiddenColumn', 'nested'] as const;
```
(:1–:10)

**Flow:** every public/shared list route funnels its query through sanitizePublicQuery FIRST, deleting exactly getHiddenColumn (bypasses the getAst allowedCols gate to emit all non-system columns) and nested (drives caller-controlled LTAR expansion) → THEN sharedViewQueryHelpers confines column REFERENCES inside where/sort/filterArrJson/group-by by intersecting per leaf/term against exposed columns, keeping unresolvable names harmlessly.
**Invariant:** deleting a whole KEY is reserved for switches whose only purpose is privilege escalation — anything compositional (a where clause naming five columns) must DEGRADE per-term so a multi-field search still returns the allowed fields instead of failing open. The comment block is the design contract: adding a third blocked key requires proving it's a pure bypass switch. EE's optimized path additionally intersects caller `fields` because sanitize doesn't strip them (CE ignores fields anyway).
**Probe:** `cd packages/nocodb && grep -c "getHiddenColumn\|nested" src/helpers/publicQuerySanitizer.ts` (=3: comment×2 + const) and `grep -rn "sanitizePublicQuery" src/services/public-datas.service.ts | wc -l` (=9 incl import+comment+call sites).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "sanitizePublicQuery PUBLIC_QUERY_BLOCKED_KEYS restrictSharedViewQuery", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the minimal-key delete + separate per-term reference confinement split; adapt blocked keys to YOUR AST escape hatches; omit if your public API whitelists params from scratch. Coverage caveat: grep-pinned only.
