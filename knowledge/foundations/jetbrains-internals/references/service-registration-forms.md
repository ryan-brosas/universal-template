<!-- capsule-v2 -->
# Service registration forms — interface/impl pairs with headless variants

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PlatformExtensions.xml); Codebase Memory `jetbrains-pycharm`. **Question:** How are long-lived services declared so consumers get an interface while the container picks implementations — including headless-specific ones?

## applicationService / projectService
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:META-INF/PlatformExtensions.xml` (single `<idea-plugin>` wrapper, hundreds of service declarations; PythonCore plugin.xml adds 33 applicationService + 11 projectService).
**Signature:** `<applicationService|projectService [serviceInterface="FQN"] serviceImplementation="FQN" [headlessImplementation="FQN"] [testServiceImplementation="FQN"]/>`.
**Data Shape:** interface optional (concrete-only services omit it); headless/test variants let the SAME contract resolve different classes by environment; scope = application vs project lifetime.

### Decisive source
```xml
<applicationService
  serviceInterface="com.intellij.diagnostic.StartUpPerformanceService"
  serviceImplementation="com.intellij.platform.ide.diagnostic.startUpPerformanceReporter.IdeStartUpPerformanceService"
  headlessImplementation="com.intellij.platform.diagnostic.startUpPerformanceReporter.HeadlessStartUpPerformanceService"
/>
<applicationService serviceInterface="com.intellij.openapi.editor.EditorThreading"
                    serviceImplementation="...EditorThreadingImpl" />
```

**Flow:** declare → container registers lazily under the interface key → first lookup instantiates implementation chosen by current environment (GUI/headless/test) → instance cached per scope.
**Invariant:** consumers depend ONLY on serviceInterface; environment selection is container-owned — hard-coding the impl class anywhere breaks the headless/test substitution ladder. Wrong port: eager singleton instantiation in a descriptor-driven system.
**Probe:** deterministic: `unzip -p intellij.platform.ide.impl.jar META-INF/PlatformExtensions.xml | grep -B1 -A3 StartUpPerformanceService`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "startup performance reporter service", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt interface-keyed lazy services with environment-specific implementation selection; adapt scope names; omit IntelliJ container disposal semantics. Coverage caveat: direct jar read.
