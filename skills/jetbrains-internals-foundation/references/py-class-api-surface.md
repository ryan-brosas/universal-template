<!-- capsule-v2 -->
# PyClass API surface — what does the published class contract expose, and which legacy seams does it still carry?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What are the load-bearing members of the 425-line `PyClass` interface (the largest file in the published surface)?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/PyClass.java:30` — `interface PyClass extends PyAstClass, PsiNameIdentifierOwner, PyCompoundStatement, PyDocStringOwner, StubBasedPsiElement<PyClassStub>, ScopeOwner, PyDecoratable, PyTypedElement, PyQualifiedNameOwner, PyStatementListContainer, PyWithAncestors, PyTypeParameterListOwner, PyDeprecatable, PyCallSiteOwner`. Members: hierarchy `getSuperClasses(context) :101`, `getMethodsInherited :129`, `getMethods :138`; properties `findProperty(name, inherited, context) :220`, `findPropertyByCallable :305`; attributes split `getClassAttributes() :249` vs `getClassAttributesInherited(context) :261` (doc TODO :258 admits the split should collapse), `getInstanceAttributes() :273`; `getNestedClasses() :278`; checks `isSubclass(PyClass/String, context) :310/:312`; scope walk `processClassLevelDeclarations(processor) :354`.
**Signature:** context-optional overloads (`@Nullable TypeEvalContext`) throughout — legacy call sites pass null.
**Data Shape:** arrays-with-EMPTY_ARRAY constant idiom (:32-33).

### Decisive source
```java
// PyClass.java:30-38 — the interface head: FOURTEEN super-interfaces
public interface PyClass
  extends PyAstClass, PsiNameIdentifierOwner, PyCompoundStatement, PyDocStringOwner,
          StubBasedPsiElement<PyClassStub>, ScopeOwner, PyDecoratable, PyTypedElement,
          PyQualifiedNameOwner, PyStatementListContainer, PyWithAncestors,
          PyTypeParameterListOwner, PyDeprecatable, PyCallSiteOwner {
// :256-258 doc verbatim:
//   "If you need parent attributes, consider using {@link #getClassAttributesInherited(TypeEvalContext)}"
//   + "TODO: Replace it and getClassAttributes() with a single getClassAttributes(context, inherited)"
```

**Flow:** everything type/resolve/inspection-related funnels through this one interface — it is the compatibility membrane between stub world (StubBasedPsiElement), AST world (PyAstClass), and type world (PyTypedElement).
**Invariant:** null-context calls are LEGAL but mean "fallback inference" — new code must thread a real TypeEvalContext; attribute getters are NOT unified despite the in-source TODO, so inherited-vs-own is a caller decision that silently changes results.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`wc -l com/jetbrains/python/psi/PyClass.java` → `425`;
`sed -n '30,33p' com/jetbrains/python/psi/PyClass.java | grep -o ',' | wc -l` → `13` commas = 14 super-interfaces across the 3-line extends clause;
`grep -n 'TODO: Replace it' com/jetbrains/python/psi/PyClass.java` → :258.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyClass findProperty isSubclass getSuperClasses", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the member taxonomy (hierarchy/properties/attributes/nested/scope). Adapt: to your language's class model. Omit: PSI infrastructure interfaces.
