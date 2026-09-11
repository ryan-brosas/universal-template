<!-- capsule-v2 -->
# PyTypeProvider extension surface — how do plugins inject types into the Python type evaluator?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** Which hooks does a Python type-inference plugin implement, and what must every hook return when it has no opinion?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/impl/PyTypeProvider.java:30-31` — `interface PyTypeProvider` with `EP_NAME = ExtensionPointName.create("Pythonid.typeProvider")`; safe base `psi/types/PyTypeProviderBase.java:26` — `class PyTypeProviderBase implements PyTypeProvider` overriding **12** hooks (`grep -c '@Override'` → 12): `getReferenceExpressionType :28`, `getReferenceType`, `getParameterType`, `getReturnType`, `getCallType(PyFunction,PyCallSiteOwner,…)` :60 (delegates to the `PyCallSiteExpression` overload), `getContextManagerVariableType`, `getCallableType`, `getGenericType`, `getGenericSubstitutions` (returns `Collections.emptyMap()` — the one non-null default), `prepareCalleeTypeForCall`, `getMemberTypes`.
**Signature:** every hook takes `(…, @NotNull TypeEvalContext context)` and returns `@Nullable PyType` / `Ref<PyType>` / `List<PyTypeMember>`.
**Data Shape:** `Ref<PyType>` wrappers allow NULL types inside (explicit "typed as absent"); `getGenericSubstitutions` is Map-valued.

### Decisive source
```java
// PyTypeProviderBase.java:28-31, 60-65, 84-86
public @Nullable PyType getReferenceExpressionType(@NotNull PyReferenceExpression referenceExpression,
                                                   @NotNull TypeEvalContext context) { return null; }
public @Nullable Ref<PyType> getCallType(@NotNull PyFunction function, @NotNull PyCallSiteOwner callSite,
                                         @NotNull TypeEvalContext context) {
  if (callSite instanceof PyCallSiteExpression callSiteExpression) {
    return getCallType(function, callSiteExpression, context);   // bridge to expression overload
  }
  return null;
}
public @NotNull Map<PyType, PyType> getGenericSubstitutions(…) { return Collections.emptyMap(); }
```

**Flow:** TypeEvalContext walks ALL registered `Pythonid.typeProvider` extensions per query → first non-null opinion wins per its own composition policy → base class defines the no-op contract so implementers override only what they know.
**Invariant:** "return null = no opinion" is the load-bearing default — an implementation that returns a placeholder non-null type poisons downstream inference; the Map hook alone defaults to EMPTY not null. Porting this EP means porting the null-discipline, not just signatures.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c '@Override' com/jetbrains/python/psi/types/PyTypeProviderBase.java` → `12`;
`grep -n 'Collections.emptyMap()' com/jetbrains/python/psi/types/PyTypeProviderBase.java` → exactly 1 hit (:85);
descriptor half from `<install>` root: `unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -c '"Pythonid.typeProvider"'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyTypeProviderBase getReferenceExpressionType getCallType", limit: 5, fields: ["signature", "name", "file"] });
// rank-1 :28-31, rank-2 :60-65 line-exact
```

## Verdict
Adopt: nullable-opinion hook family + empty-map exception. Adapt: your TypeEval equivalent. Omit: PyCallSite bridging internals.
