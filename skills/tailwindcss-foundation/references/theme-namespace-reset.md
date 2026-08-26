<!-- capsule-v2 -->
# Theme namespace reset — how do `--ns-*: initial`, `default`, and user overrides interact when folding many `@theme` blocks into one Theme?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** When a user writes `--color-*: initial;`, which keys die, and why does `@theme default { --color-potato: … }` lose to an earlier plain `@theme` block?

## Theme.add / clearNamespace
**Path/Symbol:** `packages/tailwindcss/src/theme.ts:60-86` (`Theme.add`), `:149-166` (`clearNamespace`), `:17-39` (`ignoredThemeKeyMap` / `isIgnoredThemeKey`).
**Signature:** `add(key, value, options = ThemeOptions.NONE, src?)`; keys ending in `-*` with value `'initial'` are reset directives.
**Data Shape:** internal `Map<key, { value, options: ThemeOptions (INLINE|REFERENCE|DEFAULT|STATIC|USED bits), src }>` plus a `Set<AtRule>` of collected keyframes.

### Decisive source
```ts
if (key.endsWith('-*')) {
  if (value !== 'initial') {
    throw new Error(`Invalid theme value \`${value}\` for namespace \`${key}\``)
  }
  if (key === '--*') {
    this.values.clear()
  } else {
    this.clearNamespace(key.slice(0, -2), ThemeOptions.NONE)
  }
}

if (options & ThemeOptions.DEFAULT) {
  let existing = this.values.get(key)
  if (existing && !(existing.options & ThemeOptions.DEFAULT)) return
}

if (value === 'initial') {
  this.values.delete(key)
} else {
  this.values.set(key, { value, options, src })
}
```

**Flow:** blocks fold in document order. A wildcard key is only legal with the value `initial`; `--*: initial` wipes everything, `--ns-*: initial` deletes every key under `ns` *except* sub-namespaces listed in `ignoredThemeKeyMap` (e.g. `--font-*` keeps `--font-weight-*`/`--font-size-*`; `--text-*` keeps `--text-color-*` and friends). A `DEFAULT`-flagged add silently no-ops when a non-default value already occupies the key — later default blocks can never clobber earlier user values, but two defaults chain normally and plugin/config compat layers add after user CSS. A literal `initial` on a concrete key deletes it.
**Invariant:** Reset semantics are order-sensitive by design (last writer wins except DEFAULT); `clearNamespace`'s option mask (`ThemeOptions.NONE` = clear regardless of flags) means reference/inline variants of a namespace are also wiped. Wildcard adds throw rather than storing garbage.
**Probe:** `packages/tailwindcss/src/index.test.ts:1736` "`@theme` values can be unset" (`--color-*`, `--text-md`, `--animate-*`, `--keyframes-*` all reset in one block), :1834 "all `@theme` values can be unset at once", :1867/:1916/:2051 namespace non-interference (`--font-*` vs `--font-weight-*` etc.), :3026 "`default` theme values can be overridden by regular theme values" (`#ac855b` survives over `#efb46b`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "Theme add clearNamespace initial namespace unset keyframes", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed top hits: `theme.Theme.clearNamespace … theme.ts 149-166`, `theme.Theme.addKeyframes … theme.ts 295-297`, `theme.Theme.namespace … theme.ts 276-293`, `theme.Theme.add … theme.ts 60-86`.

## Verdict
Adopt the fold-in-order Theme algebra: wildcard resets with protected sub-namespaces, DEFAULT-loses-to-user precedence, and `initial` as delete. Adapt the protected-sub-namespace table to your token vocabulary. Omit Tailwind's specific ignored-key list unless you need drop-in `@theme` compatibility for its default namespaces.
