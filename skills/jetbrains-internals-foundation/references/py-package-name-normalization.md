<!-- capsule-v2 -->
# Package-name normalization rules — how are Python distribution names canonicalized for comparison?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What exact normalization does `PyPackageName` apply, and where does the `__future__` carve-out bite?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/packaging/PyPackageName.kt` — `@JvmInline value class PyPackageName private constructor(val name)` with companion factories: `normalizeProjectName(name)` (PEP 503-style: lowercase, non-`[a-z0-9-]` → `-`, collapse runs, trim) and `normalizePackageName(packageName)` :30-43: trim → strip surrounding quotes → **underscore guard** `if (!name.startsWith("_")) name = name.replace('_', '-')` (:36-38, comment `// e.g. __future__`) → dots → hyphens → lowercase.
**Signature:** two distinct normalizers — project names vs package/import names.
**Data Shape:** value class wraps the canonical string; construction ONLY via the normalizing factories.

### Decisive source
```kotlin
// PyPackageName.kt:35-39
      // e.g. __future__
      if (!name.startsWith("_")) {
        name = name.replace('_', '-')
      }
```

**Flow:** any user/packaging-metadata string → normalize → compare/match against normalized installed names → display uses original, matching always uses canonical form.
**Invariant:** leading underscores are PRESERVED (`__future__`, `_pytest` stay underscored) while interior ones become hyphens (`Django_Lint` → `django-lint`) — a porter applying PEP 503 blindly breaks stdlib/dunder-package matching; quote-stripping exists because requirements files may carry `"pkg"`.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -n 'startsWith("_")' com/jetbrains/python/packaging/PyPackageName.kt` → 1 hit :37;
`grep -c 'normalizeProjectName\|normalizePackageName' com/jetbrains/python/packaging/PyPackageName.kt` → occurrence-exact 3;
`grep -c "removePrefix" com/jetbrains/python/packaging/PyPackageName.kt` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyPackageName normalizePackageName value class", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dual-normalizer split + underscore carve-out. Adapt: to your ecosystem's naming spec. Omit: none — rule is fully self-contained.
