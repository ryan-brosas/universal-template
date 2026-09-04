<!-- capsule-v2 -->
# Name-resolution shortcut ladder — how does the shipped API test "is this call `dict(...)`?" cheaply vs correctly?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the FQNamesProvider pattern and its three-tier cost/accuracy trade (`isName` / `isNameShortCut` / `isCalleeShortCut`)?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/nameResolver/{FQNamesProvider.java,NameResolverTools.java,PythonFQDNNames.java}`. Interface: `String[] getNames()` + `boolean isClass()` + default `alwaysCheckQualifiedName() = true`. Tools: `isElementWithName(elements, providers…)` :57 (any element), `isNameShortCut(element, providers…)` :76 — *"Aliases not supported, but much lighter"* (compares LAST name component only), `isName(element, providers…)` :90 — *"May be heavy"* full-FQN check wrapped in `RecursionManager.doPreventingRecursion` + a `PsiCacheKey<Pair<String,String>, PyElement>` cache :44. Vocabulary class `PythonFQDNNames.java:16`: `DICT_CLASS = new PythonFQDNNames(true, "dict") // TODO: Add other dict-like types`.
**Signature:** `FQNamesProvider` implemented by enum-like final classes holding `(isClass, names…)`.
**Data Shape:** names array = one or more FQNs per constant; defensive clone in `getNames()`.

### Decisive source
```java
// NameResolverTools.java:74-79
/**
 * Same as {@link #isName(PyElement, FQNamesProvider...)} for named elements, but only checks name.
 * Aliases not supported, but much lighter that way
 */
public static boolean isNameShortCut(...)
// :86-89: "Checks if FQ element name is one of provided names. May be <strong>heavy</strong>.
//  It is always better to use less accurate but lighter isCalleeShortCut/isNameShortCut"
```

**Flow:** caller picks tier: shortcut (name-only, alias-blind, cheap) for hot paths → full FQN resolve (recursion-guarded, cached) for correctness-critical paths → the provider vocabulary keeps target names declarative and testable.
**Invariant:** shortcut tier MUST NOT be used where imports may be aliased (`import dict as d` defeats it) — the lighter API's doc states the limitation inline; recursion guard on the heavy path is mandatory because FQN resolution itself resolves.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src/com/jetbrains/python` root:
`grep -c 'public static boolean is' nameResolver/NameResolverTools.java` → `7` (isElementWithName/isNameShortCut/isName/isCalleeShortCut/isContainsName×2 overloads/isSubclass);
`sed -n '16p' PythonFQDNNames.java` → DICT_CLASS line verbatim;
`grep -n 'RecursionManager.doPreventingRecursion' nameResolver/NameResolverTools.java` → ≥1 hit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "NameResolverTools isNameShortCut FQNamesProvider getNames", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: tiered match-cost ladder + declarative FQN vocabulary. Adapt: your cache/recursion guards. Omit: PSI key internals.
