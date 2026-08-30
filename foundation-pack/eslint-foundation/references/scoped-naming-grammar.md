<!-- capsule-v2 -->
# Scoped-package naming grammar — how do you normalize plugin/config names between shorthand, scoped, and full forms?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do `@scope`, `foo`, `@scope/foo`, and Windows backslash paths all resolve to one canonical package name per prefix?

## naming.js trio
**Path/Symbol:** `lib/shared/naming.js:normalizePackageName(name, prefix)` (:16–63), `getShorthandName(fullname, prefix)` (:71–90), `getNamespaceFromTerm(term)` (:97–100).
**Signature:** prefix is `"eslint-plugin" | "eslint-config" | "eslint-formatter"`.
**Data Shape:** scoped shortcut regex `^(@[^/]+)(?:/(?:${prefix})?)?$` maps `@z` AND `@z/`-forms to `@z/<prefix>`; insertion regex `^@([^/]+)/(.*)$` → `@$1/<prefix>-$2` only when second segment doesn't already start with the prefix.

### Decisive source
```js
if (normalizedName.includes("\\")) normalizedName = normalizedName.replace(/\\/gu, "/"); // GH issue 5644
const scopedPackageShortcutRegex = new RegExp(`^(@[^/]+)(?:/(?:${prefix})?)?$`, "u");
const scopedPackageNameRegex = new RegExp(`^${prefix}(-|$)`, "u");   // -|$ so @z/eslint-config-x counts
...
} else if (!normalizedName.startsWith(`${prefix}-`)) {
  normalizedName = `${prefix}-${normalizedName}`;                     // unscoped shorthand
}
```

**Flow:** slash-normalize → scoped? (shortcut-expand or prefix-insert-if-missing) → else plain prefix-prepend when missing.
**Invariant:** the `-|$` boundary prevents double-prefixing `@z/eslint-config-foo` while still matching bare `@z/eslint-config`; getShorthandName inverts exactly these two shapes (returns `@z` for `@z/prefix`, `@z/rest` for `@z/prefix-rest`). Backslash normalization must run BEFORE scoping checks or `@z\foo` never matches the scoped grammar — a recorded Windows regression (#5644). This module is the reason configs can be referenced as `"@z"` or `"foo"` anywhere in flat config.
**Probe:** `tests/lib/shared/naming.js` (:19–38 normalizePackageName table incl. `@z\foo` → `@z/eslint-config-foo` :23–25 and multi-segment path preservation; :40–56 getShorthandName; :58–62 getNamespaceFromTerm).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "normalizePackageName getShorthandName getNamespaceFromTerm", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.naming.normalizePackageName" });
```

## Verdict
Adopt for any plugin namespace with npm-scoped packages; keep the order (normalize separators → scope → prefix); adapt prefixes.
