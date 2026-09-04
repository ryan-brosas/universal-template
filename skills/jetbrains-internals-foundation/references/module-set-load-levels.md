<!-- capsule-v2 -->
# Module-set load levels — generated DAG with embedded/optional loading

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214`; Codebase Memory `jetbrains-pycharm`. **Question:** How does the platform ship a large module graph with explicit load semantics per node?

## Module sets
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:META-INF/intellij.moduleSets.core.lang.xml` (auto-generated; "Source: see moduleSet(\"core.lang\") function in UltimateModuleSets.kt"; nested region comments encode the DAG) + `META-INF/intellij.moduleSets.*.xml` family (~30 files).
**Signature:** `<content namespace="jetbrains"><module name="intellij.libraries.jackson" loading="embedded"/><module name="intellij.libraries.jackson.dataformat.toml"/></content>` inside `<idea-plugin>`.
**Data Shape:** `loading` absent = default; `embedded` = loaded with the host module, no separate classloader gate; consumers reference modules via `<dependencies><module name=.../>`. Region comments (`<!-- region nested: a > b -->`) document the containment path.

### Decisive source
```xml
<!-- Note: Files are kept under VCS to support running products without dev mode (deprecated) -->
<idea-plugin>
  <content namespace="jetbrains">
    <!-- region nested: core.ide > core.platform > libraries.platform > libraries.jackson2 -->
    <module name="intellij.libraries.jackson.annotations" loading="embedded"/>
    <module name="intellij.libraries.jackson" loading="embedded"/>
    <module name="intellij.libraries.jackson.dataformat.xml"/>
```
And the optional consumer side (PythonCore plugin):
```xml
<module name="intellij.python.community.communityOnly" loading="optional">
```

**Flow:** product/plugin includes a module set → each module loads at its declared level (default lazily, embedded eagerly alongside parent, required eagerly, optional on first use/dependency resolution).
**Invariant:** loading level is declared AT THE MODULE NODE, not at the consumer — a porter who puts eagerness on the dependency edge breaks lazy startup. Wrong port: flattening the set into one plugin and losing per-module gating.
**Probe:** deterministic: `unzip -p lib/intellij.platform.ide.impl.jar META-INF/intellij.moduleSets.core.lang.xml | grep -c 'loading="embedded"'` → dozens of embedded library modules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "terminal shell integration prompt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declarative per-module load levels for big capability graphs; adapt level names; omit the deprecated no-dev-mode rationale. Coverage caveat: direct jar read.
