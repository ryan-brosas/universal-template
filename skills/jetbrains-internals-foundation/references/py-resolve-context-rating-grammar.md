<!-- capsule-v2 -->
# Resolve context and result-rating grammar — how are multi-resolve candidates ordered and what do the context flags gate?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** How does the published API shape resolve requests (`PyResolveContext`) and rank their results (`RatedResolveResult`, `Pythonid.resolveResultRater`)?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/resolve/PyResolveContext.java` — immutable value object over three flags + context: factory `defaultContext(TypeEvalContext)` :43 = `(false, true, false)` (zero-arg overload `@Deprecated(forRemoval)` :38-41), `implicitContext :52` = `(true, true, false)` ("duck typing and guesses… slower; one-off user actions ONLY"), `noProperties :56` = `(false,false,false)`; wither-style copies `withTypeEvalContext/withoutImplicits/withRemote` :60/:64/:68; value semantics via equals/hashCode folding all four fields. Rating constants `psi/resolve/RatedResolveResult.java`: `RATE_HIGH = 1000` :57, `RATE_NORMAL = 0` :62, `RATE_PY_FILE_OVERLOAD = -200` :65, `RATE_LOW = -1000` :70; rater EP `psi/impl/PyResolveResultRater.java:11` `Pythonid.resolveResultRater` with two rate hooks `getImportElementRate(target)` / `getMemberRate(member,type,context)`.
**Signature:** `List<RatedResolveResult> resolveName(PyQualifiedExpression, TypeEvalContext)` (the reference-resolve provider contract).
**Data Shape:** rates are ints; higher sorts first in multiResolve lists; `isValidResult()` = element != null.

### Decisive source
```java
// PyResolveContext.java:47-52
/**
 * Allow searching for dynamic usages based on duck typing and guesses during resolve.
 * Note that this resolve context is slower than the default one. Use it only for one-off user actions.
 */
public static @NotNull PyResolveContext implicitContext(@NotNull TypeEvalContext context) {
  return new PyResolveContext(true, true, false, context);
}
// RatedResolveResult.java:66-69: "If in doubt, use 0."
```

**Flow:** caller picks flag profile (default vs implicit vs noProperties) → providers run under those gates (implicits=duck typing, allowProperties=property getters count as attributes, remote=cross-interpreter resolve) → results carry int rates → rater extensions supply the canonical rate for imports/members → UI sorts descending.
**Invariant:** contexts are IMMUTABLE — every change returns a new instance (wither pattern), so mutating-in-place is unportable; `implicitContext` must stay out of batch/indexing paths (documented perf trap); RATE_PY_FILE_OVERLOAD being NEGATIVE encodes "python-file overload loses to normal results" — sign matters.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`sed -n '57p;62p;65p;70p' com/jetbrains/python/psi/resolve/RatedResolveResult.java` → the four constants verbatim;
`grep -n 'implicitContext\|noProperties' com/jetbrains/python/psi/resolve/PyResolveContext.java | head -3` → :52/:56;
`grep -c 'getImportElementRate\|getMemberRate' com/jetbrains/python/psi/impl/PyResolveResultRater.java` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyResolveContext implicitContext RatedResolveResult RATE_HIGH", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: tri-flag immutable resolve context + signed-rate ordering vocabulary. Adapt: your resolve pipeline's flag set. Omit: IntelliJ PsiPolyVariantReference mechanics.
