<!-- capsule-v2 -->
# Class/module member-provider pair — how do plugins complete classes and modules with members resolved through PsiPaths?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the two-EP contract for `Pythonid.pyClassMembersProvider` / `Pythonid.pyModuleMembersProvider` and the module-side QName indirection?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/types/PyClassMembersProvider.java` — interface, EP field `Pythonid.pyClassMembersProvider`, two hooks: `Collection<PyCustomMember> getMembers(PyClassType clazz, PsiElement location, TypeEvalContext)` and `PsiElement resolveMember(PyClassType type, String name, PsiElement location, PyResolveContext)`. Twin `PyModuleMembersProvider.java` — ABSTRACT class, EP `Pythonid.pyModuleMembersProvider`; template method `getMembers(module, PointInImport, context)` :30 resolves the module's importable name via `PyPsiFacade.getInstance(...).findShortestImportableName(vFile, module)` then delegates to abstract `getMembersByQName(module, qName, context)` :37; `resolveMember` :51 loops members matching by name and calls `o.resolve(module, resolveContext)`.
**Signature:** class-side = direct hooks; module-side = implement ONE method (`getMembersByQName`), get lookup/resolve free.
**Data Shape:** members are `PyCustomMember`s (see py-custom-member-builder); `PointInImport` distinguishes usage position inside an import statement.

### Decisive source
```java
// PyModuleMembersProvider.java:30-41
public @NotNull Collection<PyCustomMember> getMembers(@NotNull PyFile module,
                                                      @NotNull PointInImport point,
                                                      @NotNull TypeEvalContext context) {
  final VirtualFile vFile = module.getVirtualFile();
  if (vFile != null) {
    final String qName = PyPsiFacade.getInstance(module.getProject()).findShortestImportableName(vFile, module);
    if (qName != null) {
      return getMembersByQName(module, qName, context);
    }
  }
  return Collections.emptyList();
}
```

**Flow:** completion asks both providers → class provider keys on the TYPE, module provider keys on the module's shortest importable name → resolve re-walks the same member list and delegates to each member's own `resolve()`.
**Invariant:** the module provider's template-method shape is deliberate — contributors think in qualified names ("what does module `os.path` expose?"), NOT in PSI files; returning members whose names collide with real attributes shadows the real ones silently.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'getMembersByQName' com/jetbrains/python/psi/types/PyModuleMembersProvider.java` → `2` (:37 delegate + :68 abstract declaration; the class-side interface `PyClassMembersProvider` carries getMembers/resolveMember, NO QName API);
`grep -n 'findShortestImportableName' com/jetbrains/python/psi/types/PyModuleMembersProvider.java` → exactly 1 hit;
`grep -c '"Pythonid.pyClassMembersProvider"\|"Pythonid.pyModuleMembersProvider"' com/jetbrains/python/psi/types/PyClassMembersProvider.java com/jetbrains/python/psi/types/PyModuleMembersProvider.java` → sums to `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyModuleMembersProvider getMembersByQName findShortestImportableName", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: two-level member injection keyed by type vs module-QName; keep resolve symmetric with get. Adapt: your facade for importable names. Omit: PointInImport enumeration details.
