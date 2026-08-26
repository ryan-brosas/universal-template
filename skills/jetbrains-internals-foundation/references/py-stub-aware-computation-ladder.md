<!-- capsule-v2 -->
# Stub-aware computation ladder — how does analysis produce identical results whether the file is stubbed or fully loaded?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** How do you write Python PSI analysis that never flips results when a file's AST availability changes (open tab, cache eviction)?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/impl/StubAwareComputation.java:75` — `public final class StubAwareComputation<Psi extends PsiElement, CustomStub, Result>`; builder entry `:76-80 on(Psi)`; branch setters `overStub :157`, `overAst :170`, `overAstStubLike :182`, `withStubBuilder :192`; terminal `Result compute(TypeEvalContext) :200`.
**Signature:** `StubAwareComputation.on(element).overAst(fn).overStub(fn).overAstStubLike(fn).compute(context)` → `Result`; or `.withStubBuilder(buildStub)` replacing `overAstStubLike`.
**Data Shape:** three computation arms keyed by context state; `compute` dispatches on `context.maySwitchToAST(psi)` FIRST, then `psi.getStub() != null`.

### Decisive source
The class javadoc (:33-73) states the contract verbatim:
```java
if (context.maySwitchToAST(psi)) {
  return processOverAst(psi);
}
else if (psi.getStub() != null) {
  return processOverStub(psi.getStub());
}
else {
  return processOverAstStubLike(psi);
}
```
plus the trap sentence: *"it means deliberately dumbing down the analysis, even though a full AST is available, just in order to avoid flaky results"* and *"quite easy to get wrong, e.g. by accidentally switching the first two conditions."*

**Flow:** `maySwitchToAST` true → full AST arm; false but stub present → stub arm; false and no stub → astStubLike arm (AST-computed but STUB-SHAPE semantics).
**Invariant:** all three arms must return IDENTICAL results for the same logical input — the ladder exists because index-time (stubs only) vs editor-time (AST) analyses that diverge make inspections flake depending on which files happen to be open. Swapping arms 1 and 2 is THE named wrong port.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'maySwitchToAST' com/jetbrains/python/psi/impl/StubAwareComputation.java` → `4` (:33/:197 javadoc `{@link}`s + :39 doc example + :215 real dispatch);
`grep -c 'public @NotNull StubAwareComputation<Psi, CustomStub, Result> over' com/jetbrains/python/psi/impl/StubAwareComputation.java` → `3` (overStub/overAst/overAstStubLike at :157/:170/:182).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "StubAwareComputation compute overAstStubLike", limit: 5, fields: ["signature", "name", "file"] });
// compute Method lib/src/.../StubAwareComputation.java 200-224
```

## Verdict
Adopt: three-arm identical-results discipline for any stub/index dual representation. Adapt: your own "may switch" predicate. Omit: IntelliJ PSI/stub plumbing specifics.
