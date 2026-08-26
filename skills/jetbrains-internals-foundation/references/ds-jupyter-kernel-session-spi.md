<!-- capsule-v2 -->
# Jupyter execution/session SPI — where does a notebook host plug in kernel sessions, servers, and interrupts so each interpreter stays a pure contribution?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/jupyter-plugin/lib/jupyter-plugin.jar` `META-INF/plugin.xml` (136,834-byte shared-infra descriptor). Codebase Memory `jetbrains-dataspell` (jar plane; deterministic unzip probes). **Question:** What is the complete extension-point catalog for connecting, launching, configuring, and interrupting Jupyter kernels, and how do default vs language-specific implementations coexist on the same EP?

## Eight dynamic interface EPs; defaults declared order="last", interpreters override by plain contribution
**Path/Symbol:** `jupyter-plugin.jar:META-INF/plugin.xml` — EP declarations :51 (`connectionProvider`), :52 (`notebookSessionFactory`), :66 (`…execution.core.jupyterKernelInterruptHandler`), :67 (`jupyterManagedServerConfigurationProvider`), :72 (`jupyterServersFactory`), :87 (`jupyterManagedServerExecutionServiceProvider`), :91 (`executionSettingsProvider`), :94 (`kernelInstaller`) — all `dynamic="true"` interface EPs under namespace `com.intellij.jupyter.core`.
**Signature:** `<extensionPoint qualifiedName="com.intellij.jupyter.core.notebookSessionFactory" interface="com.intellij.jupyter.core.executor.kernel.session.JupyterNotebookSessionFactory" dynamic="true"/>` (pattern holds for all eight).
**Data Shape:** Python contributions (:1150-1195, `defaultExtensionNs="com.intellij.jupyter.core"`): 3× `notebookSessionFactory` — `IPyKernelSessionFactory` (plain), `ExternalJupyterlabNotebookSessionFactory` (plain), `ManagedJupyterlabNotebookSessionFactory order="last"` (fallback); `jupyterServersFactory id="default" → JupyterLabServersFactory`; `jupyterManagedServerExecutionServiceProvider → JupyterManagedServerExecutionServiceService`; 2× Windows interrupt handlers. The CORE module block (:727) contributes the base interrupt handler: `JupyterByRequestKernelInterruptHandler order="last"`. `kernelInstaller`, `executionSettingsProvider`, and `jupyterManagedServerConfigurationProvider` are DECLARED but carry no contribution in this descriptor — they are filled by consumers/hosts elsewhere.

### Decisive source
```xml
<!-- EP declarations: every seam is an interface + dynamic -->
<extensionPoint qualifiedName="com.intellij.jupyter.core.connectionProvider" interface="…JupyterConnectionProvider" dynamic="true"/>
<extensionPoint qualifiedName="com.intellij.jupyter.core.notebookSessionFactory" interface="…JupyterNotebookSessionFactory" dynamic="true"/>
<extensionPoint qualifiedName="com.intellij.jupyter.core.jupyter.connections.execution.core.jupyterKernelInterruptHandler"
                interface="…JupyterKernelInterruptHandler" dynamic="true"/>

<!-- core block: base impl reserves the fallback slot -->
<jupyter.connections.execution.core.jupyterKernelInterruptHandler
  implementation="…action.JupyterByRequestKernelInterruptHandler" order="last"/>          <!-- :727 -->

<!-- python block: three session factories, managed server demoted to last-resort -->
<notebookSessionFactory implementation="…ipykernel.IPyKernelSessionFactory"/>              <!-- :1161 -->
<notebookSessionFactory implementation="…managed.ExternalJupyterlabNotebookSessionFactory"/><!-- :1162 -->
<notebookSessionFactory implementation="…managed.ManagedJupyterlabNotebookSessionFactory" order="last"/> <!-- :1163 -->
<jupyter.connections.execution.core.jupyterServersFactory id="default"
  implementation="…server.JupyterLabServersFactory"/>                                      <!-- :1183 -->
<jupyter.connections.execution.core.jupyterKernelInterruptHandler
  implementation="…ipykernel.IPyKernelWindowsNativeInterruptHandler"/>                     <!-- :1187 -->
```

**Flow:** connection settings are discovered via `connectionProvider`s → a session is created by iterating `notebookSessionFactory`s (first acceptor wins; `Managed…` explicitly `order="last"` so real interpreters always beat the generic managed-server fallback) → server lifecycle goes through `jupyterServersFactory id="default"` / `jupyterManagedServer*Provider`s → per-kernel setup through `kernelInstaller` + `executionSettingsProvider` → interruption walks the handler chain: OS-native Windows handlers first, `JupyterByRequestKernelInterruptHandler order="last"` as the portable by-request fallback.
**Invariant:** ordering IS the selection policy — the base/generic implementation always declares `order="last"` instead of being absent, so an empty chain still works and any concrete contribution wins without touching the base. All eight EPs are `dynamic="true"`, so kernels/servers can hot-swap. The two Windows interrupt handlers ride the same EP as the portable one — platform specialization is just another ordered contribution.
**Probe:** deterministic jar probes (executed byte-for-byte this pass):
```bash
unzip -p plugins/jupyter-plugin/lib/jupyter-plugin.jar META-INF/plugin.xml \
  | grep -nE 'extensionPoint (qualifiedName|name)="[^"]*(connectionProvider|notebookSessionFactory|kernelInstaller|jupyterServersFactory|InterruptHandler|managedServer|ManagedServer)'   # hits at :51,:52,:66,:67,:72,:87,:91,:94
unzip -p … | grep -nE '<(connectionProvider|notebookSessionFactory|jupyterKernelInterruptHandler|jupyterManagedServerExecutionServiceProvider|jupyterServersFactory)'   # :727, :1161-1163, :1183-1184, :1187-1188
```

## Get live surrounding code
**Retrieve:** jar plane not symbol-indexed; graph anchor for the consumer side:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "jupyter kernel session connection SPI executor", limit: 8 });
// returns descriptor-free helpers plane only — confirming the SPI itself lives in the jar plane (coverage caveat recorded)
```

## Verdict
Adopt: an execution SPI published as a flat set of dynamic interface EPs with explicit `order="last"` generic fallbacks; id-keyed singleton services (`id="default"`); declared-but-unfilled EPs as invitation points for hosts. Adapt factory interfaces and ordering vocabulary to your kernel model. Omit the managed-server provider pair if you have no server-hosting persona; omit Windows-native interrupt handlers on non-Windows targets.
