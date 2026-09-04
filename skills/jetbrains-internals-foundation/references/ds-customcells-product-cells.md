<!-- capsule-v2 -->
# DataSpell customCells fragment family — how does a product layer private notebook cell kinds over shared infra without the infra knowing about them?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/dataspell-plugin/lib/dataspell-plugin.jar` descriptor plane (jar-root `intellij.dataspell.jupyter.customCells*.xml` twins of the CDATA embedded in `META-INF/plugin.xml`). Codebase Memory `jetbrains-dataspell` (descriptors are not symbol-indexed; deterministic unzip probes below). **Question:** How do you add product-specific notebook cell types (data input, variable forms, visualization, data-wrangling) on top of a language-neutral notebook infrastructure plugin, keeping each kind independently loadable and gated?

## Parent declares one EP + FUS listener; four siblings consume it under `defaultExtensionNs="com.intellij.jupyter"`
**Path/Symbol:** `dataspell-plugin.jar:intellij.dataspell.jupyter.customCells.xml` (parent), `…customCells.{data,variables,visualization,dataWrangler}.xml` (siblings); parent wiring mirrored as `<module>`+CDATA content nodes in `META-INF/plugin.xml` (:96, :129, :195, :251).
**Signature:** parent: `<extensionPoint qualifiedName="com.intellij.jupyter.cellDataFrameProvider" interface="…JupyterCellDataFrameProvider" dynamic="true"/>` + `<applicationListeners>` `JupyterDsCustomCellsUsageReporter` on topic `com.intellij.jupyter.core.fus.JupyterNotebookUsageListener`. Siblings contribute via `<extensions defaultExtensionNs="com.intellij.jupyter"><cellDataFrameProvider implementation=…/>`.
**Data Shape:** parent module `visibility="internal"`, depends only on shared jupyter modules (`intellij.jupyter.core/py/psi`, `intellij.notebooks.visualization`). Each sibling re-declares its own dependency set and layers exactly the seams its cell kind needs. Every sibling cell kind is gated by a default-on registry key (`dataspell.variable.cells.menu.enabled`, `dataspell.variable.checkbox|text|dropdown|number.cell.enabled`, `dataspell.visualization.cell.enabled`, `datawrangler.plugin.jupyter.cells`) so support can be killed at runtime.

### Decisive source
```xml
<!-- intellij.dataspell.jupyter.customCells.xml — the WHOLE parent -->
<idea-plugin package="com.intellij.dataspell.jupyter.customCells" visibility="internal">
  <dependencies>
    <module name="intellij.jupyter.core"/>
    <module name="intellij.jupyter.py"/>
    <module name="intellij.jupyter.psi"/>
    <module name="intellij.notebooks.visualization"/>
  </dependencies>
  <applicationListeners>
    <listener class="…JupyterDsCustomCellsUsageReporter"
              topic="com.intellij.jupyter.core.fus.JupyterNotebookUsageListener"/>
  </applicationListeners>
  <extensionPoints>
    <extensionPoint qualifiedName="com.intellij.jupyter.cellDataFrameProvider"
                    interface="…JupyterCellDataFrameProvider" dynamic="true"/>
  </extensionPoints>
```
```xml
<!-- siblings CONSUME it in the jupyter namespace, not com.intellij -->
<extensions defaultExtensionNs="com.intellij.jupyter">
  <cellDataFrameProvider implementation="…data.JupyterDataCellDataFrameProvider"/>
  <core.jupyter.connections.execution.jupyterCellTaskBuilder
    implementation="…data.run.JupyterDataInputTableTaskBuilder"/>
</extensions>
```

**Flow:** shared `intellij.jupyter` infra stays product-blind → parent customCells module declares the product's single integration EP (`cellDataFrameProvider`) plus a usage-telemetry listener → four sibling modules opt into the parent by `<module name="intellij.dataspell.jupyter.customCells"/>` and each contributes: a `jupyterCellTypeProvider` per cell kind (checkbox/text/dropdown/number/visualization/dataWrangler), an `inputFactory` per editor widget, a `jupyterCellTaskBuilder` for execution, toolbar actions anchored `before NotebookDeleteCellAction` / `after NotebookInsertDataInputCellAction`, and Python insight plugs (completion.contributor, pyReferenceResolveProvider, inspectionExtension skipper) only where the cell is Python-backed.
**Invariant:** the infra namespace `com.intellij.jupyter` is the ONLY coupling point — no sibling ever edits infra behavior; each cell kind is removable by registry key or by dropping its module, and the remaining kinds keep working because they share nothing but the parent's EP. Cross-sibling reuse is declared explicitly (dataWrangler depends on `customCells.data` + `sql.common`; visualization depends on `intellij.dataspell.charteditor`).
**Probe:** deterministic jar probes (executed byte-for-byte this pass):
```bash
unzip -l plugins/dataspell-plugin/lib/dataspell-plugin.jar | grep customCells   # 5 xml entries + plugin.xml wiring
unzip -p plugins/dataspell-plugin/lib/dataspell-plugin.jar intellij.dataspell.jupyter.customCells.xml
unzip -p plugins/dataspell-plugin/lib/dataspell-plugin.jar META-INF/plugin.xml | grep -c "customCells"   # 66
```

## Get live surrounding code
**Retrieve:** descriptors/jar plane is not symbol-indexed by design; retrieval is the pinned unzip probe above plus the graph anchor for the consuming infra:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "notebookSpecification LanguageExtensionPoint jupyter core", limit: 5 }); // infra-side anchor (see jupyter-shared-infra-plugin capsule)
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/dataspell-plugin/lib/dataspell-plugin.jar"] });
// -> not symbol-indexed (jar): status recorded as coverage caveat, decisive excerpts read from unzipped descriptors directly
```

## Verdict
Adopt: product cells as sibling modules around ONE parent-declared integration EP consumed in the host namespace; per-kind registry kill-switches; telemetry listener at the parent so usage reporting exists even if all siblings drop out; execution/task-builder + type-provider + input-factory triad per kind. Adapt the EP names and action anchors to your notebook host. Omit the DataSpell-specific SQL-conversion and chart-editor dependencies unless your cells need database backends.
