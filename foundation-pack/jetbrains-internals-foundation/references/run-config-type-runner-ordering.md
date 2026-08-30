<!-- capsule-v2 -->
# Run-configuration type/runner ordering — how do contributors sequence themselves against platform defaults?

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`intellij.python.community.impl.xml` inside `plugins/python-ce/lib/modules/intellij.python.community.impl.jar`); Codebase Memory `jetbrains-pycharm`. **Question:** When several plugins contribute `configurationType`/`programRunner` extensions for the SAME runtime, what decides who wins the Run dialog slot and who executes first?

## Run/Debug extension block (community impl module)
**Path/Symbol:** `plugins/python-ce/lib/modules/intellij.python.community.impl.jar:intellij.python.community.impl.xml:288-304` (`<extensions defaultExtensionNs="com.intellij">` → Run/Debug region).
**Signature:** `<configurationType implementation="<ConfigurationType FQN>" [order="first|last|before|after <anchor-id>"]/>`; `<programRunner implementation="<ProgramRunner FQN>" order="..."/>`.
**Data Shape:** every contribution carries only an implementation FQN plus optional `order`; there is NO explicit priority number — sequencing is purely relational (named anchors or first/last). Anchor ids are either class FQNs of other contributions (`intellij.platform.dap.DapProgramRunner`) or short runner-id strings returned by `getRunnerId()` (`defaultRunRunner`, `defaultDebugRunner`).

### Decisive source
```xml
<programRunner implementation="com.jetbrains.python.run.PythonRunner" order="before defaultRunRunner"/>
<programRunner implementation="com.intellij.python.debugger.PythonDebugProgramRunner"
               order="before intellij.platform.dap.DapProgramRunner, before defaultDebugRunner"/>
```
Anchor-resolution proof (runner ids are CODE constants, not XML ids): `lib/intellij.platform.execution.impl.jar` contains `com/intellij/execution/runners/DefaultRunProgramRunner` whose constant pool carries `defaultRunRunner` next to `getRunnerId ()Ljava/lang/String;`. Cross-product corroboration of the same grammar with different anchors: WebStorm `plugins/nodeJS/lib/nodeJS.jar:META-INF/plugin.xml:77` uses `<programRunner order="before node-js.run.program.runner" .../>`.

**Flow:** platform registers its default runner under id `defaultRunRunner` → Python module declares `PythonRunner` with `order="before defaultRunRunner"` so any plain "Run file" resolves to the Python executor first → debugger runner chains TWO anchors (DAP generic runner AND platform debug runner) to sit before both → absent an anchor, contribution order is unspecified.
**Invariant:** ordering is DECLARED RELATIVE TO NAMED PEERS, never absolute; an anchor that names a non-existent id silently degrades to unspecified position (same degrade rule recorded in extension-ordering-attributes). Wrong port: assuming XML declaration order decides priority, or hard-coding "first" — that breaks the moment another product layer contributes its own runner.
**Probe:** deterministic jar read: `unzip -p plugins/python-ce/lib/modules/intellij.python.community.impl.jar intellij.python.community.impl.xml | sed -n '301,303p'` → shows both order attributes verbatim; `unzip -p lib/intellij.platform.execution.impl.jar | grep -ac 'defaultRunRunner'` → ≥1 proves the anchor id exists in the platform binary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PydevTestRunner class runfiles", limit: 10, fields: ["signature", "name", "file"] });
```
(the graph's code plane holds the runners' helper side, e.g. `plugins/python-ce/helpers/pydev/_pydev_runfiles/pydev_runfiles.py:277-810`; the manifest plane itself is jar-resident XML — retrieve by direct unzip, see Probe.)

## Verdict
Adopt relative named-anchor ordering for competing implementations of one capability contract; adapt anchor naming to your host's registration ids (FQN or stable short id); omit IntelliJ's ProgramRunner execution machinery itself. Coverage caveat: manifest read from jar; anchor-existence proven via class-constant scan, not decompilation.
