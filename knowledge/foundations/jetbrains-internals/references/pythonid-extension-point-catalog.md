<!-- capsule-v2 -->
# Pythonid extension-point catalog — which extension points does the shipped Python open-api surface expose?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What is the complete list of `Pythonid.*` extension points declared in code (not just XML), and where does each live?

## Connected graph-selected seam
**Path/Symbol:** 15 `ExtensionPointName.create("Pythonid.<name>")` sites across `lib/src/pycharm-openapi-src/com/jetbrains/python/**` (grep census `grep -rn "ExtensionPointName.create"` → 15 hits, one per EP):
`psi/types/engine/PyTypeEngineProvider.kt` → `Pythonid.typeEvalTypeEngineProvider`; `psi/resolve/PyCanonicalPathProvider.java` → `canonicalPathProvider`; `psi/PyCustomPackageIdentifier.java` → `customPackageIdentifier`; `psi/impl/PyImportResolver.java` → `importResolver`; `inspections/PyInspectionExtension.java` → `inspectionExtension`; `psi/impl/PyKeywordArgumentProvider.java` → `keywordArgumentProvider`; `psi/types/PyClassMembersProvider.java` → `pyClassMembersProvider`; `psi/types/PyEnumMemberDeclarationProvider.kt` → `pyEnumMemberDeclarationProvider`; `psi/types/PyModuleMembersProvider.java` → `pyModuleMembersProvider`; `psi/resolve/PyReferenceResolveProvider.java` → `pyReferenceResolveProvider`; `documentation/PythonDocumentationQuickInfoProvider.java` → `pythonDocumentationQuickInfoProvider`; `psi/impl/PyResolveResultRater.java` → `resolveResultRater`; `inspections/PyStatementEffectQuickFixProvider.java` → `statementEffectQuickFixProvider`; `psi/resolve/PyThirdPartySdkDetector.java` → `thirdPartySdkDetector`; `psi/impl/PyTypeProvider.java` → `typeProvider`.
**Signature:** Java form: `ExtensionPointName<T> EP_NAME = ExtensionPointName.create("<name>")` as an interface field; Kotlin form: `private val EP_NAME = ExtensionPointName.create<T>("...")` inside the companion object.
**Data Shape:** all 15 names also appear in `META-INF/plugin.xml` inside `plugins/python-ce/lib/python-ce.jar` (each `grep -c '"Pythonid.<ep>"'` on the extracted descriptor → 1 declaration); the descriptor declares 70 `Pythonid.*` EP names TOTAL — i.e. ~55 more EPs exist whose interfaces are NOT part of this published src surface (implementation-level extension).

### Decisive source
```
$ cd lib/src/pycharm-openapi-src
$ grep -rln "ExtensionPointName.create" . | wc -l
15
$ grep -o '"Pythonid\.[a-zA-Z.]*"' <(unzip -p ../../../../plugins/python-ce/../lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml) | sort -u | wc -l
70
```
(second number from extracted `/tmp/jb14_python_plugin.xml`: 70 unique `"Pythonid.*"` strings)

**Flow:** code declares the typed EP constant → descriptor declares the EP bean/class → extensions contribute implementations → the 15-code-vs-70-descriptor delta marks which contracts JetBrains considers stable enough to publish source for.
**Invariant:** the code-side name string and the descriptor-side `name=` attribute MUST match exactly (namespace `Pythonid.` prefix included) or contributions silently bind to nothing; when porting, publish BOTH halves together.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -rln "ExtensionPointName.create" com/jetbrains/python | wc -l` → `15`;
`grep -rc '"Pythonid.inspectionExtension"' com/jetbrains/python/inspections/PyInspectionExtension.java` → `1`.
Descriptor half (from `<install>` root): `unzip -p plugins/python-ce/lib/python-ce.jar META-INF/plugin.xml | grep -c '"Pythonid.typeProvider"'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyReferenceResolveProvider EP_NAME resolveName", limit: 10, fields: ["signature", "name", "file"] });
// resolves PyReferenceResolveProvider.java with the EP_NAME field line-exact
```

## Verdict
Adopt: the 15-name catalog as the stable extension checklist for a Python IDE-like product. Adapt: rename namespace to your product id. Omit: the ~55 implementation-only descriptor EPs (no published contract).
