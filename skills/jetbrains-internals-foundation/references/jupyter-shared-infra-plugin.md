<!-- capsule-v2 -->
# Jupyter shared-infrastructure plugin — how do you ship notebook machinery once and let Python/Kotlin/R notebooks all consume it, without the infra plugin exposing features of its own?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84` (proprietary distribution; study/reference use only). Codebase Memory `jetbrains-dataspell`. **Question:** What makes `intellij.jupyter` a shared component rather than a feature plugin, and how does per-kernel-language behavior plug in?

## Non-standalone plugin + per-language beanClass EP with <with>
**Path/Symbol:** `plugins/jupyter-plugin/lib/jupyter-plugin.jar:META-INF/plugin.xml` (136,834 bytes; embedded CDATA modules per the v2 content model) — decisive module `intellij.jupyter.core`.
**Signature:** `<extensionPoint qualifiedName="com.intellij.jupyter.core.notebookSpecification" beanClass="com.intellij.lang.LanguageExtensionPoint" dynamic="true"><with attribute="implementationClass" implements="com.intellij.jupyter.core.core.api.lang.NotebookSpecification"/></extensionPoint>`.
**Data Shape:** infra EPs are interface-keyed singletons (`connectionProvider`, `notebookSessionFactory`, `editor.jupyterRemoteSessionHistoryRetrieverProvider`, `jupyterActionPresentationModifier`, `notebookToolWindowSelector`) plus exactly one LANGUAGE-keyed EP (`notebookSpecification`) whose implementations are per-language `LanguageExtensionPoint` beans keyed by `language=`.

### Decisive source
```xml
<description><![CDATA[This plugin is a shared component that provides common Jupyter notebook
infrastructure for other JetBrains plugins. It does not provide standalone features and is not
intended to be installed directly. … install one of the following plugins (they will bring this
plugin as a dependency automatically): Python … Kotlin Notebook … R Plugin]]></description>
<dependencies>
  <plugin id="com.intellij.notebooks.core" />
  <plugin id="org.intellij.plugins.markdown" />
</dependencies>
```

**Flow:** generic notebook/file-model plumbing lives in `com.intellij.notebooks.core` → `intellij.jupyter` adds Jupyter-specific PSI (`intellij.jupyter.psi`: Jupyter language, parser definition, view-provider chooser, nbformat cell-type provider) and core services (kernel sessions, connections, run-action handling) → each kernel-language plugin depends on the infra plugin and contributes its `notebookSpecification` so run/edit behavior specializes by language without infra-side switches.
**Invariant:** the infra plugin declares ZERO end-user surface — its own description forbids direct installation; every capability must arrive as an extension contributed by a consumer or an internal module (`visibility="internal"`). The `beanClass=LanguageExtensionPoint` + `<with implements=…NotebookSpecification>` pair keeps N kernel languages from becoming N forks: new language = one contribution, no infra edit. DataSpell layers product cells the same way — `plugins/dataspell-plugin/lib/dataspell-plugin.jar:intellij.dataspell.jupyter.customCells.xml` (jar-root descriptor) declares `<extensionPoint qualifiedName="com.intellij.jupyter.cellDataFrameProvider" interface="…JupyterCellDataFrameProvider" dynamic="true"/>` plus a FUS listener on topic `com.intellij.jupyter.core.fus.JupyterNotebookUsageListener`: extending the host vocabulary, never editing it.
**Probe:** from the plugins dir (pins non-standalone status, language-keyed EP shape, product-layer EP):
```bash
cd /mnt/hdd/utopia/inspo/dataspell/plugins && unzip -p jupyter-plugin/lib/jupyter-plugin.jar META-INF/plugin.xml | grep -c 'does not provide standalone features'   # -> 1
unzip -p jupyter-plugin/lib/jupyter-plugin.jar META-INF/plugin.xml | grep -A1 'notebookSpecification' | grep -c 'implements='                                            # -> 1
unzip -p dataspell-plugin/lib/dataspell-plugin.jar intellij.dataspell.jupyter.customCells.xml | grep -c 'cellDataFrameProvider'                                          # -> 1
```

## Get live surrounding code
Descriptor plane not symbol-indexed; Retrieve is the unzip probe above. Cross-check consumer-side tokens live in the graph:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "jupyter customCells dataframe provider", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "notebook session factory kernel", limit: 5 });
```

## Verdict
Adopt: extract notebook/execution machinery into a non-installable infra plugin; expose ONE language-keyed `LanguageExtensionPoint` spec EP (+ narrow interface SPIs for session/connection) so kernel languages integrate by contribution. Adapt EP names and the PSI module split to your host. Omit marketplace metadata and the minified `jupyter-web/*` bundles (obfuscated chunk soup — no portable contract). Coverage caveat: claims rest on whole-descriptor reads at DS-261.26222.84; consumer classes are compiled (strings-level corroboration only).
