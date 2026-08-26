<!-- capsule-v2 -->
# Selector factory validate/create ladder — how do you turn a stored (type, expression) pair into a selector object with validation errors a user can act on?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** Where should the type-switch live that validates and instantiates pluggable selector kinds, and how do parse failures become field-level validation violations?

## One engine, one type switch, violation-wrapped failures
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/SelectorFactory.java:validateSelector,createSelector` (:37–97).
**Signature:** `void validateSelector(final String type, final String expression) throws ConstraintViolationException`; `Selector createSelector(final String type, final String expression)`.
**Data Shape:** in: `type` ∈ {`jexl` (JexlSelector.TYPE), `csel` (CselSelector.TYPE)} + raw expression; out: `JexlSelector` (evaluate-only) or `CselSelector` (evaluate + toSql); invalid ⇒ `ConstraintViolationException` carrying one violation on field `"expression"`.

### Decisive source
```java
private final JexlEngine jexlEngine = new JexlEngine();   // one sandboxed engine per factory

public void validateSelector(final String type, final String expression) {
  try {
    switch (type) {
      case JexlSelector.TYPE:
        jexlEngine.parseExpression(expression);
        break;
      case CselSelector.TYPE:
        validateCselExpression(jexlEngine.parseExpression(expression));   // csel = parse + AST grammar walk
        break;
      default:
        throw new IllegalArgumentException("Unknown selector type: " + type);
    }
  }
  catch (Exception e) {
    String detail = format("Invalid %s: %s", upper(type),
        e instanceof JexlException ? expandExceptionDetail((JexlException) e) : e.getMessage());
    throw new ConstraintViolationException(e.getMessage(),
        ImmutableSet.of(constraintViolationFactory.createViolation("expression", detail)));
  }
}

public Selector createSelector(final String type, final String expression) {
  boolean shouldTrimLeadingSlash = false;
  switch (type) {
    case JexlSelector.TYPE:
      return new JexlSelector(jexlEngine.buildExpression(expression, shouldTrimLeadingSlash));
    case CselSelector.TYPE:
      return new CselSelector(cselToSql, jexlEngine.buildExpression(expression, shouldTrimLeadingSlash));
    default:
      throw new IllegalArgumentException("Unknown selector type: " + type);
  }
}
```

**Flow:** REST/UI layer calls `validateSelector` on submit → unknown types fail fast; `jexl` needs only parseability while `csel` additionally passes the parsed script through the `CselValidator` grammar whitelist → every failure path (parse, grammar, unknown-type) funnels into one catch that rethrows as `ConstraintViolationException` bound to the `expression` form field → at use time `createSelector` repeats the same switch and compiles against the same shared engine.
**Invariant:** validation and creation must agree — the same (type, expression) that passes `validateSelector` is exactly what `createSelector` accepts, so there is no accept-then-fail-later window; the exception message never leaks stack traces, only the humanized detail.
**Probe:** no dedicated `SelectorFactoryTest` exists anywhere in the tree (graph name search: 0 hits). Behavior pinned indirectly by `CselValidatorTest.java` (`failsToParseInvalidContentSelectors` :46–49, `failsToParseCoordinateContentSelectors` :51–54 ⇒ both reach the factory's catch as JexlException) and `JexlSelectorTest` pretty-exception trio (:64–107). Record as partial direct-test coverage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "SelectorFactory validateSelector createSelector constraint violation selector type", limit: 10 });
```
Live result (2026-08-26): 1,381 total hits, top rows = `validateSelector` (:59–81), `createSelector` (:86–96), `constraintViolationFactory` field, plus the injected `ConstraintViolationFactory` from nexus-validation.

## Verdict
Adopt the single shared-engine factory with one exhaustive type switch serving both validate and create, and the funnel-everything-into-a-field-violation pattern for user-submitted expressions. Adapt the two concrete types to your own selector SPI (add cases per kind; keep unknown ⇒ hard error). Omit the Pro-era `coordinate.*` identifier support — this OSS tree rejects it (`hasCoordinates()` sniffs but CSEL whitelist allows only `format`/`path`). Caveat: factory itself is untested directly; keep its logic trivial enough to eyeball.
