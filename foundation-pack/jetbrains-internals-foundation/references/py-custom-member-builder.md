<!-- capsule-v2 -->
# PyCustomMember builder grammar — how do plugins declare synthetic members on classes/modules they don't own?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the fluent DSL for injecting fake-but-resolvable members (e.g. ORM fields, framework magic attributes), and where does resolution actually land?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/codeInsight/PyCustomMember.java:33` — `class PyCustomMember extends UserDataHolderBase`; fluent setters `resolvesTo(String moduleQName)` :98, `resolvesToClass(classQName)` :103, `toClass/toFunction/toFunctionRecursive/toClassAttribute/toCall/toAssignment/toPsiElement` :139-169, `alwaysResolveToCustomElement()` :134 (sets `myAlwaysResolveToCustomElement` :52), `asFunction()`/`asClassVar()`, `withIcon`, `withCustomTypeInfo` :285 (asserts type present). Resolution: `resolve(context, resolveContext)` :198 — direct target short-circuit :199-201; type-name lookup cached via `ParameterizedCachedValue` keyed `RESOLVE` with `PsiModificationTracker.MODIFICATION_COUNT` dependency :205-213; THE GUARD `:215`: `if (resolveTarget instanceof PyFunction && !myAlwaysResolveToCustomElement) return resolveTarget;`; final delegation to service `PyCustomMemberProvider.getInstance().createPyCustomMemberTarget(...)` :221-223 (`codeInsight/PyCustomMemberProvider.java` — abstract app service, 25-line file).
**Signature:** `new PyCustomMember(name, typeName, resolveToInstance).resolvesToClass("django.models.Model").toClass("objects")…`.
**Data Shape:** member = name + optional target PSI + optional PsiPath + optional type-name + flags (resolveToInstance, function, classVar, alwaysResolveToCustomElement).

### Decisive source
```java
// PyCustomMember.java:214-217 — the function-passthrough guard
final PsiElement resolveTarget = findResolveTarget(context, resolveContext);
if (resolveTarget instanceof PyFunction && !myAlwaysResolveToCustomElement) {
  return resolveTarget;   // resolve to the REAL function unless overridden
}
// javadoc on the field (:46-51): "Force resolving to …MyInstanceElement even if element is function"
```

**Flow:** provider returns members for a class/module → user code references one → `resolve()` finds the PsiPath target → functions pass through by default (you get the real method) → otherwise a synthetic `PyTypedElement` is created by the provider SERVICE so navigation/completion have a concrete element.
**Invariant:** the guard order matters — real-function passthrough beats synthetic-element creation UNLESS `alwaysResolveToCustomElement()` was called; cached class-by-QName lookups MUST depend on `MODIFICATION_COUNT` or stale targets survive edits.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'public PyCustomMember to\|public PyCustomMember resolvesTo' com/jetbrains/python/codeInsight/PyCustomMember.java` → `9`;
`sed -n '215p' com/jetbrains/python/codeInsight/PyCustomMember.java` → the guard line verbatim;
`grep -c 'abstract' com/jetbrains/python/codeInsight/PyCustomMemberProvider.java` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyCustomMember resolvesToClass alwaysResolveToCustomElement", limit: 5, fields: ["signature", "name", "file"] });
// resolvesToClass :103-106 rank-1 line-exact
```

## Verdict
Adopt: builder + passthrough-guard + provider-service split for synthetic-member injection. Adapt: your member model. Omit: Swing Icon details.
