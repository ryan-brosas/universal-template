<!-- capsule-v2 -->
# External type-engine provider — how can a whole alternative type engine be plugged into the Python evaluator?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is `Pythonid.typeEvalTypeEngineProvider` and how does its first-wins selection work?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/psi/types/engine/PyTypeEngineProvider.kt` — interface with default `fun createResolver(module: Module): PyTypeEngine? = null` :11; companion EP `private val EP_NAME = ExtensionPointName.create<PyTypeEngineProvider>("Pythonid.typeEvalTypeEngineProvider")` :18-19; selector `createTypeResolver(module)` :23-26 = `EP_NAME.extensionList.firstNotNullOfOrNull { it.createResolver(module) }`. Engine contract in sibling `PyTypeEngine.kt` (resolver invoked by TypeEvalContext for elements the built-in engine cannot type).
**Signature:** `(Module) -> PyTypeEngine?`, module-scoped (per-project-module resolution context).
**Data Shape:** first NON-NULL resolver wins; all-null ⇒ built-in engine handles everything.

### Decisive source
```kotlin
// PyTypeEngineProvider.kt:22-26
  fun createTypeResolver(module: Module): PyTypeEngine? {
    return EP_NAME.extensionList.firstNotNullOfOrNull { it.createResolver(module) }
  }
```

**Flow:** TypeEvalContext hits an element its own inference can't type → asks the engine obtained via this provider → external engine answers or declines (null) → decline falls through to next provider, finally to built-in.
**Invariant:** this is a WHOLE-ENGINE delegation point (coarse), unlike `Pythonid.typeProvider`'s per-hook opinions (fine); ordering between providers is extension-list order and the first non-null captures ALL queries — a heavy engine registered early starves later ones. Declining must be cheap.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -n 'firstNotNullOfOrNull' com/jetbrains/python/psi/types/engine/PyTypeEngineProvider.kt` → 1 hit;
`grep -c 'typeEvalTypeEngineProvider' com/jetbrains/python/psi/types/engine/PyTypeEngineProvider.kt` → `1`;
descriptor half from `<install>` root: `unzip -p plugins/python-ce/lib/python-ce.jar META-INF/plugin.xml | grep -c '"Pythonid.typeEvalTypeEngineProvider"'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyTypeEngineProvider createTypeResolver PyTypeEngine", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: coarse engine-delegation EP beside fine-grained type hooks. Adapt: selection policy if you need priority weights. Omit: engine internals (not shipped).
