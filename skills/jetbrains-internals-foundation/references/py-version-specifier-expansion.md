<!-- capsule-v2 -->
# Version-specifier expansion semantics — how do PEP 440 compatible-release and Poetry caret/tilde collapse into comparison pairs?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** How does `PyVersionSpecifiers` normalize `~=`, `~`, `^` specifiers — and where do the three expansion tables DIFFER?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/packaging/PyVersionSpecifiers.kt`. Parse entry `parseSingleSpecifier(spec) :51-66`: split operator/version at FIRST digit, strip trailing `.*`, dispatch `"~=" → expandCompatibleRelease :69`, `"~" → expandTilde :83`, `"^" → expandCaret :98`, else `VersionConstraintOperator.parse`; empty operator string parses as EQUAL (:199 `"=", "==", "" -> EQUAL`). Operator enum :178-206 = 6 members with `isSatisfiedBy(comparisonResult)` mapping and symbol parse table. Missing-component comparison policy `PythonVersionValue.compareTo(other, operator) :135-149`.
**Signature:** every expansion returns `listOf(MORE_OR_EQUAL to version, LESS to upper)` — a PAIR, never a single bound.
**Data Shape:** version = Triple(major, minor?, patch?); expansions produce upper bounds with explicit +1 on the last significant component.

### Decisive source
```kotlin
// :68-80 (compatible release)   /** ~=3.8 → >=3.8, <4.0;  ~=3.8.5 → >=3.8.5, <3.9.0 */
// :82-95 (Poetry tilde)         /** ~3.8 → >=3.8, <3.9;  ~3.8.5 → >=3.8.5, <3.9.0 */
//   tilde: minor==null ⇒ upper = major+1          ← differs from ~= on "3.8"
// :97-112 (Poetry caret)        /** ^3.8 → >=3.8, <4.0;  ^0.8 → >=0.8, <0.9 */
//   caret upper ladder: major!=0 → major+1; else minor!=0 → minor+1; else patch+1
// :137-143 compareTo defaults: "<",">=" fill missing with 0; "<=",">" fill with 20 ("any subversion"); "==","!=" match any
```

**Flow:** specifier string → operator+version → either one comparison pair or an expansion pair → all pairs ANDed by `isValid` against a candidate Python version.
**Invariant:** the three operators are NEAR-twins that diverge exactly when minor is absent: `~=3.8` → `<4.0` but `~3.8` → `<3.9`; caret adds the 0-major rule (`^0.8` → `<0.9`) which the other two lack. Porting one table for all three is THE wrong port. The magic `20` in compareTo is deliberate ("any subversion") — not a typo to fix.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'expandCompatibleRelease\|expandTilde\|expandCaret' com/jetbrains/python/packaging/PyVersionSpecifiers.kt` → counts ≥6 lines (defs + call sites; occurrence-exact via `grep -o | wc -l` = 6: 2 defs + 4 call sites);
`sed -n '97p' com/jetbrains/python/packaging/PyVersionSpecifiers.kt` → caret doc line verbatim;
`sed -n '178,184p' com/jetbrains/python/packaging/PyVersionSpecifiers.kt` → 6 enum constants.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyVersionSpecifiers isValid parseSingleSpecifier", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: expansion-to-comparison-pairs normalization + the per-operator divergence table. Adapt: your version value type. Omit: pre-release/epoch handling (explicitly unsupported here).
