<!-- capsule-v2 -->
# Notification group contract — declare the channel before emitting

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** How does the platform force every notification into a pre-declared, user-controllable channel?

## notificationGroup
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (15 `<notificationGroup .../>` declarations; platform EPs `com.intellij.notification.group` / `notification.parentGroup` in PlatformExtensionPoints.xml).
**Signature:** `<notificationGroup id="G" displayType="BALLOON|STICKY_BALLOON|TOOL_WINDOW" [isLogByDefault="true"] [hideFromSettings="true"] [toolWindowId="T"] [bundle="messages.B" key="title.k"]/>`.
**Data Shape:** id = emitter-facing handle; displayType = presentation contract (balloon/sticky/tool-window); toolWindowId binds TOOL_WINDOW type to an existing window; bundle/key externalize the group title.

### Decisive source
```xml
<notificationGroup id="Python.Internal" displayType="BALLOON" isLogByDefault="true" hideFromSettings="true" />
<notificationGroup id="PyProject.toml" displayType="STICKY_BALLOON" isLogByDefault="true"
                   bundle="messages.PyProjectTomlBundle" key="pyproject.notification.title" />
<notificationGroup id="Python Debugger" displayType="TOOL_WINDOW" toolWindowId="Debug"
                   bundle="messages.PyBundle" key="debug.notification.group" />
```

**Flow:** plugin declares groups up front → emitters create notifications referencing `id` only → settings UI exposes per-group control (unless hideFromSettings) → undeclared ids are rejected.
**Invariant:** emission REQUIRES a declared group — you cannot invent a channel at the call site. Wrong port: letting feature code pass ad-hoc titles/levels; that reintroduces notification spam with no user control.
**Probe:** deterministic: `grep -oE '<notificationGroup id="[^"]*"' py-plugin.xml | wc -l` → 15 declared channels for 100+ potential emit sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "notification balloon", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declared-channel discipline for any user-visible event stream; adapt display types; omit IntelliJ balloon internals. Coverage caveat: direct jar read.
