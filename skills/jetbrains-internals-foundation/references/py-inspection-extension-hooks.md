<!-- capsule-v2 -->
# Inspection-extension ignore hooks — how do plugins silence specific inspection findings declaratively?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the full suppression-hook vocabulary of `Pythonid.inspectionExtension`?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/inspections/PyInspectionExtension.java:24-25` — `abstract class PyInspectionExtension` + `EP_NAME = ExtensionPointName.create("Pythonid.inspectionExtension")`; **13** `public boolean ignore*` methods (census `grep -c 'public boolean ignore'` → 13).
**Signature:** each hook takes the analyzed element (+ often `TypeEvalContext`) and returns boolean.
**Data Shape:** the hook set, by suppression target — unused locals (`ignoreUnused` :27), shadowed names (:31), missing docstrings (:35), parameters-from-usage contributions (`getFunctionParametersFromUsage` :39 — List<String>, not a boolean), method-parameters check (:48), package-name-in-requirements (:52), unresolved references (:63), forced enable/disable via tri-state (`Boolean overrideUnresolvedReferenceInspection(file)` :72 — true=force-on, false=force-off, null=default), unresolved members (:84), protected-symbol access (:95), `__init__`/`__new__` signature mismatch pairs (:99), no-effect statements (:109), trailing semicolons (:119), interpreter warnings (:129), unused imports (:136).

### Decisive source
```java
/**
 * @return true -- Enable forcibly, false -- disable forcibly, null -- act as usual.
 */
public Boolean overrideUnresolvedReferenceInspection(@NotNull PsiFile file) {   // :72
```
```java
/** @return Do not report "unused import" */
public boolean ignoreUnusedImports(@NotNull PyImportedNameDefiner importNameDefiner) { return false; }  // :136
```

**Flow:** each inspection consults all extensions before reporting → ANY true suppresses → the tri-state hook additionally lets an extension flip a whole inspection on/off for a file regardless of its own verdicts.
**Invariant:** defaults are all "don't interfere" (false/null) — a porter who makes a hook throw or return true-by-default silently disables inspections product-wide; the tri-state Boolean (not boolean) distinction IS the API for force-enable.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'public boolean ignore' com/jetbrains/python/inspections/PyInspectionExtension.java` → `13`;
`grep -n 'overrideUnresolvedReferenceInspection' com/jetbrains/python/inspections/PyInspectionExtension.java` → `:72`;
`grep -c '"Pythonid.inspectionExtension"' com/jetbrains/python/inspections/PyInspectionExtension.java` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyInspectionExtension ignoreUnresolvedReference overrideUnresolvedReferenceInspection", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the ignore-hook taxonomy + tri-state override as the shape of a suppression API. Adapt: hook names to your inspection catalog. Omit: the inspections consuming them (not in this src snapshot).
