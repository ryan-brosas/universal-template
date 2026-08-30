<!-- capsule-v2 -->
# Notebook LSP wiring — how do you attach an LSP-based language server to notebook cells while keeping the host IDE from double-reporting diagnostics?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84` (proprietary distribution; study/reference use only). Codebase Memory `jetbrains-dataspell`. **Question:** Which extensions bind a notebook language to the platform LSP stack, and why does the Python-specific wiring live in an OPTIONAL descriptor fragment?

## serverSupportProvider + inspectionSuppressor pair behind an optional fragment
**Path/Symbol:** `plugins/dataspell-jupyter-lsp/lib/dataspell-jupyter-lsp.jar` — `META-INF/plugin.xml` (1,470 B) + `META-INF/python.xml` (825 B, loaded only when `PythonCore` is present); classes `com/intellij/dataspell/jupyter/lsp/instances/python/{JupyterLspPython,PyLsp,Pylance}.class`.
**Signature:** `<depends optional="true" config-file="python.xml">PythonCore</depends>` → `<platform.lsp.serverSupportProvider implementation="…JupyterLspPythonServerSupportProvider"/>`; `<lang.inspectionSuppressor language="JupyterPython" implementationClass="…JupyterLspPythonInspectionSuppressor"/>`; child configurable `id="settings.jupyter-lsp.python" parentId="settings.jupyter-lsp"`.
**Data Shape:** base plugin depends on `intellij.jupyter.psi`, `intellij.jupyter.core`, `intellij.notebooks.core`, `intellij.platform.lsp`, `intellij.platform.lsp.impl`; declares its own `notificationGroup id="Jupyter LSP"` (STICKY_BALLOON) + `statistics.notificationIdsHolder` before use.

### Decisive source
```xml
<idea-plugin package="com.intellij.dataspell.jupyter.lsp">
  <dependencies>
    <plugin id="intellij.jupyter" />
    <module name="intellij.jupyter.psi" />
    <module name="intellij.platform.lsp" />
    <module name="intellij.platform.lsp.impl" />
  </dependencies>
  <depends optional="true" config-file="python.xml">PythonCore</depends>
</idea-plugin>

<!-- META-INF/python.xml, loaded only with PythonCore present -->
<extensions defaultExtensionNs="com.intellij">
  <platform.lsp.serverSupportProvider implementation="com.intellij.dataspell.jupyter.lsp.client.JupyterLspPythonServerSupportProvider"/>
  <lang.inspectionSuppressor language="JupyterPython" implementationClass="com.intellij.dataspell.jupyter.lsp.client.JupyterLspPythonInspectionSuppressor"/>
</extensions>
```

**Flow:** plugin boots with notebook+LSP modules only (works without Python) → when the host has PythonCore, the optional fragment registers the server-support provider that spawns/attaches the LSP instance per notebook (`PyLsp`, `Pylance` instance classes) → because the LSP now owns diagnostics/completions/hover for `JupyterPython`, the paired `inspectionSuppressor` mutes the IDE-internal inspectors on those files so users never see doubled squiggles → settings nest as a child configurable under the parent Jupyter LSP page.
**Invariant:** the suppressor is not cosmetic cleanup — shipping server diagnostics WITHOUT the same-language suppression produces duplicate error channels, and shipping the suppressor WITHOUT a live server hides real errors. They are one contract. The optional-fragment split keeps the plugin installable in hosts lacking Python while every Python-specific class stays unreferenced until load (see `optional-depends-capability-fragment` for the fragment mechanics this instance exercises).
**Probe:**
```bash
cd /mnt/hdd/utopia/inspo/dataspell/plugins && unzip -p dataspell-jupyter-lsp/lib/dataspell-jupyter-lsp.jar META-INF/plugin.xml | grep -c 'config-file="python.xml"'                       # -> 1
unzip -p dataspell-jupyter-lsp/lib/dataspell-jupyter-lsp.jar META-INF/python.xml | grep -oE 'serverSupportProvider|inspectionSuppressor' | sort | uniq -c                                  # -> 1 each, same fragment
unzip -l dataspell-jupyter-lsp/lib/dataspell-jupyter-lsp.jar | grep -c 'instances/python/Pylance\|instances/python/PyLsp'                                                                  # -> 2
```

## Get live surrounding code
Descriptor plane not symbol-indexed (unzip probes above are the Retrieve primitive). Graph-side cross-check of the indexed helpers plane:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "jupyter lsp server support provider", limit: 5 });
```

## Verdict
Adopt: LSP-over-notebook = one `serverSupportProvider` extension + a SAME-language `inspectionSuppressor`, packaged so interpreter-specific wiring rides an optional config-file fragment. Adapt provider/suppressor names and the settings nesting to your host. Omit the vendored Pylance integration details (proprietary third-party protocol glue). Coverage caveat: whole-descriptor reads at DS-261.26222.84; instance classes corroborated by class-name listing only.
