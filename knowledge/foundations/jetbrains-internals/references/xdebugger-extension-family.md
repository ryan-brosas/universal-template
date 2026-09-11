<!-- capsule-v2 -->
# xdebugger EP family — how does the platform let any language plug breakpoints, attach targets, and debugger settings into ONE debug UI?

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (`lib/intellij.platform.debugger.impl.jar:intellij.platform.debugger.impl.content.xml` [218 lines whole] + `lib/intellij.platform.debugger.impl.ui.jar:intellij.platform.debugger.impl.ui.xml`); consumers: `plugins/python-ce/lib/modules/intellij.python.community.impl.xml:307-310`, WebStorm `plugins/javascript-debugger/lib/javascript-debugger.jar:META-INF/plugin.xml:149-151`, Rider `intellij.rider.plugins.unity.backend.xml` xdebugger block. Codebase Memory `jetbrains-pycharm`. **Question:** What is the minimal extension set a language must contribute to appear in the shared debugger, and which platform-side EPs customize it?

## The EP catalog (platform declares, languages consume)
**Path/Symbol:** declaration plane A = `intellij.platform.debugger.impl.content.xml:9-17` (8 core EPs: `xdebugger.debuggerSupport`, `attachHostProvider`, `attachDebuggerProvider`, `attachHostSettingsProvider`, three `dialog.*presentation/process.view.provider`s, `breakpointCustomTooltipProvider`); declaration plane B = UI module :48-58 (7 more: `debuggerTabCustomizer`, `nodeLinkActionProvider`, `inlineValuePopupProvider`, `hotSwapUiExtension`, `customEvaluateHandler`, `customMuteBreakpointHandler`, `customQuickEvaluateActionProvider`) plus the `xdebugger.breakpointGroupingRule` ×3 and `breakpointType`/`settings`/`customXDescriptorSerializerProvider` EPs consumed cross-product.
**Signature:** `<extensionPoint qualifiedName="com.intellij.xdebugger.<name>" interface="com.intellij.xdebugger...<Interface>" dynamic="true"/>`; consumption is namespaced `<xdebugger.breakpointType implementation="..."/>` inside `defaultExtensionNs="com.intellij"`.
**Data Shape:** consumer counts at unchanged pin: Python contributes 4 (2 breakpointTypes + settings + attachDebuggerProvider), JavaScript-debugger 6 (incl. customXDescriptorSerializerProvider), Unity 3 (attachDebuggerProvider + Pausepoint breakpointType + dialog item presentation provider). The platform itself consumes its own dialog EPs once (default presentation providers).

### Decisive source
```xml
<!-- platform declares (impl.content.xml:9-12) -->
<extensionPoint qualifiedName="com.intellij.xdebugger.debuggerSupport" interface="com.intellij.xdebugger.impl.DebuggerSupport" dynamic="true"/>
<extensionPoint qualifiedName="com.intellij.xdebugger.attachHostProvider" interface="com.intellij.xdebugger.attach.XAttachHostProvider" dynamic="true"/>
<extensionPoint qualifiedName="com.intellij.xdebugger.attachDebuggerProvider" interface="com.intellij.xdebugger.attach.XAttachDebuggerProvider" dynamic="true"/>
<!-- language consumes (python.community.impl.xml:307-310) -->
<xdebugger.breakpointType implementation="com.jetbrains.python.debugger.PyLineBreakpointType"/>
<xdebugger.breakpointType implementation="com.jetbrains.python.debugger.PyExceptionBreakpointType"/>
<xdebugger.settings implementation="com.jetbrains.python.debugger.settings.PyDebuggerSettings"/>
<xdebugger.attachDebuggerProvider implementation="com.jetbrains.python.debugger.attach.PyLocalAttachDebuggerProvider"/>
```
Executor slot proof — the Debug button itself is an ordered executor contribution: `<executor implementation="com.intellij.execution.executors.DefaultDebugExecutor" order="first,after run" id="debug"/>` (:36). Platform also self-gates a listener per OS: `<listener ... class=...DebuggerFocusManager os="windows" activeInHeadlessMode="false"/>` (ui.xml:42-46).

**Flow:** IDE boot → debuggerSupport instances collected → breakpoint types registered so gutter clicks route by file type → attach providers enumerate processes/hosts for the Attach dialog (dialog EPs swap its rows/presentation) → session UI assembled from tab customizers/grouping rules; each language's settings object merges into one preferences page.
**Invariant:** EVERYTHING visual in the debug tool window is extension-shaped — no language code is hard-referenced by the platform; conversely a language that ships a breakpointType but no settings still works (defaults apply). Wrong port: declaring `xdebugger.*` contributions under your own plugin namespace — they are consumed under `defaultExtensionNs="com.intellij"` with dotted element names mirroring the qualified EP name.
**Probe:** deterministic jar reads: `unzip -p lib/intellij.platform.debugger.impl.jar intellij.platform.debugger.impl.content.xml | grep -c 'extensionPoint qualifiedName="com.intellij.xdebugger.'` → 8; same pipe on python impl XML `grep -c 'xdebugger.breakpointType'` → 2; WebStorm plugin.xml `grep -c 'xdebugger.'` → 6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "AttachDebuggerTracing pydevd_attach_to_process attach", limit: 10, fields: ["signature", "name", "file"] });
```
(verified live ×2: `jetbrains-pycharm.plugins.python-ce.helpers.debugpy._vendored.pydevd.pydevd_attach_to_process.linux_and_mac.attach.AttachDebuggerTracing` and its `helpers/pydev` twin resolve line-exact — the injected-attach half of this plane.)

## Verdict
Adopt the split between breakpoint TYPES (data), attach PROVIDERS (targets), and session CUSTOMIZERS (UI) when unifying heterogeneous debuggers behind one shell; adapt interface names to host; omit the xdebugger session machinery itself. Coverage caveat: all cited files are jar-resident XML (`no_recorded_issue`, freshness `not_tracked`); behavior runner does not exist for installed builds → deterministic probes substitute.
