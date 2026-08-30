<!-- capsule-v2 -->
# PyPsiPath target grammar — how do synthetic members point at real Python elements by name instead of by reference?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** How is "resolve to `module.Class.method`" encoded as data, and what is the recursive-search variant for?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/codeInsight/PyPsiPath.java:21` — `abstract class PyPsiPath` with single hook `resolve(context, PyResolveContext) :30`; nested targets: `ToFile(qualifiedName)` :32, `ToClassQName(qualifiedName)` :47, `ToClass(parent, className)` :60 (composes on a parent path), `ToFunction(parent, functionName)` :111, `ToFunctionRecursive` :160; both class/function finders walk with a `PyRecursiveElementVisitor` subclass (`ClassFinder :94`, `FunctionFinder :143`) and match by name.
**Signature:** `new PyPsiPath.ToClassQName("django.db.models").toClass("Model")…` — composition = parent path + child name.
**Data Shape:** path tree resolved lazily at member-resolve time against the CURRENT index state.

### Decisive source
```java
// PyPsiPath.java:60-68 — composition over direct strings
public static class ToClass extends PyPsiPath {
  public ToClass(PyPsiPath parent, String className) {
    myParent = parent;
    myClassName = className;
  }
// :103-110 ClassFinder.visitPyClass: descend, match node.getName().equals(myClassName)
```

**Flow:** `PyCustomMember.toClass/toFunction/...` build these paths → at resolve time the chain walks file→class→function by NAME → first name match wins (visitor order).
**Invariant:** targeting is BY-NAME against the live index — renaming the target breaks the link silently (no compile-time safety); that fragility is why the finder returns null rather than guessing. Compose parent+child rather than baking full dotted names when the host module may move.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -n 'class ToClass extends\|class ToFunction extends\|class ToFunctionRecursive' com/jetbrains/python/codeInsight/PyPsiPath.java` → `:60/:111/:160`;
`grep -c 'extends PyRecursiveElementVisitor' com/jetbrains/python/codeInsight/PyPsiPath.java` → `4` finder classes (`ClassFinder :94`, `FunctionFinder :143`, `CallFinder :223`, `AssignmentFinder :284`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyPsiPath ToClass ToFunctionRecursive resolve", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: name-based path trees as the data form of cross-file references in dynamic-language IDEs. Adapt: your own visitor/index. Omit: visitor plumbing specifics.
