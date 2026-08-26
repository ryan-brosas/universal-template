<!-- capsule-v2 -->
# SQL taint-brand kernel — how do I make untrusted SQL unrepresentable as executable at the type level?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How does pg-meta guarantee that only escaped/validated strings compose into executed SQL, and what is the sanctioned path for genuinely user-authored and third-party-influenced SQL?

## Branded fragment trio + tagged-template gate
**Path/Symbol:** `packages/pg-meta/src/pg-format/index.ts` : `SafeSqlFragment` / `UntrustedSqlFragment` / `DisplayableSqlFragment` (:27, :36, :39), `safeSql` (:359-367), `rawSql` (:374-376), `untrustedSql` (:383-385), `acceptUntrustedSql` (:396-398).
**Signature:** `type SafeSqlFragment = string & { readonly __safeSqlFragmentBrand: never }`; `function safeSql(strings: TemplateStringsArray, ...interpolated: Array<SafeSqlFragment>): SafeSqlFragment`.
**Data Shape:** brands are compile-time-only (`never` phantom field); runtime values are plain strings — no runtime re-validation happens anywhere in the kernel. Ownership: producers are `ident()`/`literal()`/`keyword()` outputs, static template text, or the two explicit escape hatches.

### Decisive source
```ts
export type SafeSqlFragment = string & { readonly __safeSqlFragmentBrand: never }
// UntrustedSqlFragment doc: "Safe to display; must never be auto-executed
// or persisted as user-authored content. Promote to SafeSqlFragment via
// acceptUntrustedSql() — only inside an explicit user-action event handler."
export function safeSql(
  strings: TemplateStringsArray,
  ...interpolated: Array<SafeSqlFragment>
): SafeSqlFragment {
  return strings.reduce((result, string, i) => result + string + (interpolated[i] ?? ''), '') as SafeSqlFragment
}
```

**Flow:** producer escapes value → brand attaches → `safeSql` tag accepts only branded interpolations (plain string/number/object fails type-check) → composition output is itself branded → downstream executors accept only `SafeSqlFragment`. Third-party-influenced SQL enters via `untrustedSql()` (display-only); a deliberate Run click promotes it through `acceptUntrustedSql()`; explicitly typed editor SQL enters via `rawSql()`.
**Invariant:** the ONLY ways to obtain a `SafeSqlFragment` for arbitrary input are `rawSql` (user typed it) and `acceptUntrustedSql` (user gestured approval). Never cast plain strings to the brand; never call `acceptUntrustedSql` from useEffect/render.
**Probe:** `packages/pg-meta/test/pg-format.test.ts` describe `'safeSql type safety'` — three `@ts-expect-error` tests pin that interpolating a plain string, number, or object into `safeSql` is a compile error; the injection battery (UNION SELECT / stacked DROP TABLE / comment bypass) proves the runtime escape holds.
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "safeSql untrustedSql acceptUntrustedSql branded sql format escape", limit: 40 })
// rank 1-3 = untrustedSql :383-385, acceptUntrustedSql :396-398, safeSql :359-367 (line-exact); total 25, has_more false
```

## Verdict
Adopt the three-brand vocabulary (Safe / Untrusted / Displayable) plus the event-handler-only promotion rule — it ports verbatim to any TS codebase composing SQL or shell commands. Adapt the escape-hatch call sites to your host's "user authored it" definition (SQL editor, RLS tester). Omit nothing from the invariant: if your language lacks nominal branding, emulate with a wrapper class or lint rule; a stringly-typed port silently reopens the hole.
