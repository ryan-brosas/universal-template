<!-- capsule-v2 -->
# Console customizer EP stack + PRO `order="first"` runnerFactory override — how does a base module expose console behavior seams that a paid tier re-routes without forking?

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`plugins/python-ce/lib/modules/intellij.python.community.impl.jar:intellij.python.community.impl.xml:828,856-903` [declarations] and :1315-1319 [default consumers]; `plugins/python/lib/modules/intellij.python.jar:intellij.python.xml:189,242-244` [PRO overrides]); Codebase Memory `jetbrains-pycharm`. **Question:** How do you design a console whose execution pipeline is customizable per framework AND whose default implementation can be replaced by an upper product layer?

## The seam ladder (community declares + defaults; PRO overrides)
**Path/Symbol:** declarations in the community impl descriptor's `<extensionPoints>` block: `com.jetbrains.python.console.runnerFactory` (:828-830), `...executeCustomizer` (:891-893), `...pyConsoleOutputCustomizer` (:897-899), `com.jetbrains.python.console.customizer` with attribute `id="python"` (:900-902); default consumers at :1315-1319 inside `<extensions defaultExtensionNs="com.jetbrains.python.console">`; PRO overrides in `intellij.python.xml`.
**Signature:** `<extensionPoint qualifiedName="com.jetbrains.python.console.<name>" interface="...<Interface>" dynamic="true"/>`; consumption: `<executeCustomizer implementation="<FQN>"/>`, `<customizer id="python" implementation="<FQN>"/>`; override: `<runnerFactory implementation="<FQN>" order="first"/>`.
**Data Shape:** community ships exactly ONE default per seam (`PyExecuteConsoleCustomizerDefault`, `PyConsoleOutputCustomizerDefault`, `PythonConsoleCustomizer id=python`) — defaults are ordinary contributions, not code fallbacks; PRO contributes `FrameworkAwarePythonConsoleRunnerFactory order="first"` plus `FlaskConsoleOptionsProvider` via `Pythonid.consoleOptionsProvider`.

### Decisive source
```xml
<!-- community: declare -->
<extensionPoint qualifiedName="com.jetbrains.python.console.runnerFactory" interface="com.jetbrains.python.console.PythonConsoleRunnerFactory" dynamic="true"/>
<!-- community: default consume (:1315-1319) -->
<extensions defaultExtensionNs="com.jetbrains.python.console">
  <executeCustomizer implementation="com.jetbrains.python.console.PyExecuteConsoleCustomizerDefault"/>
  <pyConsoleOutputCustomizer implementation="com.jetbrains.python.console.PyConsoleOutputCustomizerDefault"/>
  <customizer id="python" implementation="com.jetbrains.python.console.PythonConsoleCustomizer"/>
</extensions>
<!-- PRO: replace the factory, keep the contract -->
<extensions defaultExtensionNs="com.jetbrains.python.console">
  <runnerFactory implementation="com.intellij.python.pro.sdk.FrameworkAwarePythonConsoleRunnerFactory" order="first"/>
</extensions>
```
Cross-seam corroboration in the same PRO file: `<pyDebugAsyncioCustomizer implementation="...PyDebugAsyncioCustomizerImpl" order="first"/>` (:237-239) — same first-wins override grammar on a second customizer family.

**Flow:** console start → runnerFactory resolves which runner class builds the session → execute customizers transform commands before send → output customizers rewrite result rendering; PRO layer inserts its framework-aware factory ahead of the default contribution so Flask/Django consoles get extra setup WITHOUT the community module knowing PRO exists.
**Invariant:** the DEFAULT must itself be a registered extension (not a hardcoded else-branch), because ordering-based replacement only works over a homogeneous contribution list — this is run-config-type-runner-ordering's anchor grammar applied to a service-style seam. Wrong port: making the base module import the rich implementation "when present" — that inverts the dependency and breaks the layered-product split.
**Probe:** deterministic jar reads: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | grep -c 'extensionPoint qualifiedName="com.jetbrains.python.console.executeCustomizer"'` → 1; `grep -c '<executeCustomizer '` → 1; `grep -c 'customizer id="python"'` → 1; `unzip -p plugins/python/lib/modules/intellij.python.jar intellij.python.xml | grep -c 'order="first"'` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PydevTestRunner console pydev_runfiles", limit: 10, fields: ["signature", "name", "file"] });
```
(verified live: `PydevTestRunner` resolves line-exact ×2 in the helpers plane; the manifest plane itself is jar-resident XML — retrieve by direct unzip, see Probe.)

## Verdict
Adopt declare+default-in-base / order-first-replace-in-overlay as THE pattern for layered products extending a console/pipeline; adapt seam names; omit IntelliJ's console session internals. This closes pass-5's queued target #4 (console customizer stack :1315-1319 + PRO runnerFactory :243). Coverage caveat: jar-resident XML read by unzip; no behavior runner for installed-build manifests → deterministic probes substitute.
