<!-- capsule-v2 -->
# DataWrangler engine-SPI overlay plane — how does one table-transformation plugin ship a generic core, a Python engine swap, and a product overlay in the SAME jar?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/dataWrangler-plugin/lib/dataWrangler-plugin.jar` descriptors (`META-INF/plugin.xml` implementation-detail root; jar-root `intellij.dataWrangler{,.core,.impl,.jupyterPython,.jupyterPython.ds,.llm}.xml`). Codebase Memory `jetbrains-dataspell` (jar plane; deterministic unzip probes). **Question:** How do you structure an engine-agnostic data tool so the execution backend is swappable per file type AND a specific IDE can overlay extra UX without forking the plugin?

## engine EP declared in a 3-line module; core binds the default; jupyterPython swaps + overrides a facade service; `.ds.xml` overlays DataSpell UX
**Path/Symbol:** `dataWrangler-plugin.jar:intellij.dataWrangler.xml` (EP), `intellij.dataWrangler.core.xml` (default binding), `intellij.dataWrangler.jupyterPython.xml` (Python engine + facade override + own EP `com.intellij.dataWrangler.openActionExtension`), `intellij.dataWrangler.jupyterPython.ds.xml` (product overlay).
**Signature:** `<extensionPoint qualifiedName="com.intellij.dataWrangler.engine" interface="com.intellij.dataWrangler.executor.DataWranglerEngine" dynamic="true"/>`; `<projectService serviceInterface="…llm.DataWranglerFacade" serviceImplementation="…jupyterPython.facade.DataWranglerFacadeImpl"/>`.
**Data Shape:** plugin root is `implementation-detail="true"`, id `com.intellij.dataWrangler.plugin`, depends on `intellij.grid.plugin` + ultimate; module chain: `intellij.dataWrangler` (EP only) ← `.core` (binds CoreDataWranglerEngine; depends on grid/charts) ← `.impl` (UI actions; depends on database plugin) ← `.llm` ← `.jupyterPython` ("JuPy is only for py.tables"; depends on scientific tables + jupyter modules + `dataspell.jupyter.customCells.sql.backend`) ← `.ds` overlay (depends on BOTH `intellij.dataWrangler.jupyterPython` AND plugins `com.intellij.dataspell`/database).

### Decisive source
```xml
<!-- intellij.dataWrangler.xml — the whole EP module -->
<idea-plugin package="com.intellij.dataWrangler" visibility="internal">
  <extensionPoints>
    <extensionPoint qualifiedName="com.intellij.dataWrangler.engine"
                    interface="com.intellij.dataWrangler.executor.DataWranglerEngine" dynamic="true"/>
  </extensionPoints>
</idea-plugin>

<!-- intellij.dataWrangler.core.xml — default engine -->
<dataWrangler.engine implementation="com.intellij.dataWrangler.core.engine.CoreDataWranglerEngine"/>

<!-- intellij.dataWrangler.jupyterPython.xml — engine swap for py.tables + facade override -->
<dataWrangler.engine implementation="com.intellij.dataWrangler.jupyterPython.engine.PythonDataWranglerEngine"/>
<projectService serviceInterface="com.intellij.dataWrangler.llm.DataWranglerFacade"
                serviceImplementation="com.intellij.dataWrangler.jupyterPython.facade.DataWranglerFacadeImpl"/>

<!-- intellij.dataWrangler.jupyterPython.ds.xml — DataSpell overlay -->
<idea-plugin package="com.intellij.dataWrangler.jupyterPython.ds">
  <dependencies>
    …<module name="intellij.dataspell.jupyter.customCells"/><module name="intellij.dataspell.impl"/>
    <plugin id="com.intellij.database"/><plugin id="com.intellij.dataspell"/>
  </dependencies>
  <action id="DataWrangler.Toolwindow.Show" …>
    <add-to-group group-id="DataSpellDataTreePopup" anchor="first"/></action>
  <extensions defaultExtensionNs="com.intellij">
    <codeInsight.inlayProvider language="Python" … id="DWCustomOperationsInlayProvider"/>
    <dataWrangler.llm.dwCommandAction implementation="…DataWranglerCreateCustomOperation2"/>
  </extensions>
```

**Flow:** the base module publishes ONLY the engine interface → `.core` supplies a grid-based default engine that works in any IDE → `.jupyterPython` registers `PythonDataWranglerEngine` on the same EP (per-file-type selection happens at consumption) and REPLACES the `DataWranglerFacade` project service with a Python-aware impl → the `.ds` fragment (shipped inside the same plugin jar but depending on the DataSpell plugin id) adds DataSpell-tree context actions, custom-operation CRUD into `DataWrangler.Operations.Popup`, an LLM `dwCommandAction`, and a Python inlay provider for custom ops.
**Invariant:** the engine EP and facade service are the only two seams products touch; the overlay module declares its product dependency (`com.intellij.dataspell`) explicitly so it silently fails to load outside DataSpell rather than breaking the generic plugin. Custom operations are registry-gated (`datawrangler.plugin.custom.commands defaultValue="false"`).
**Probe:** deterministic jar probes (executed byte-for-byte this pass):
```bash
unzip -l plugins/dataWrangler-plugin/lib/dataWrangler-plugin.jar | grep '\.xml$'   # 6 module xmls incl. .ds twin
unzip -p … intellij.dataWrangler.xml ; unzip -p … intellij.dataWrangler.jupyterPython.xml ; unzip -p … intellij.dataWrangler.jupyterPython.ds.xml
```

## Get live surrounding code
**Retrieve:** jar plane not symbol-indexed by design; retrieval = pinned unzip probes above; graph anchors for the consumed planes:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "kotlin dataframe tables jupyter python", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/dataWrangler-plugin/lib/dataWrangler-plugin.jar", "plugins/dataWrangler-plugin/lib/jetbrains.kotlinx.dataframe.core.jar"] });
// -> jars not symbol-indexed (recorded caveat); decisive excerpts read from unzipped descriptors directly
```

## Verdict
Adopt: capability as a one-interface EP module; default engine bound by a core module; language-specific engine swap via same-EP contribution; product UX as a final overlay fragment that depends on the product plugin id and lives in the same jar. Adapt engine/facade interfaces to your domain. Omit the LLM dwCommandAction and jewel/LaF bridge dependencies unless you port the AI-command surface too.
