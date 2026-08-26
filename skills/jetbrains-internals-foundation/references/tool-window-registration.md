<!-- capsule-v2 -->
# Tool window registration — declarative docking with factory indirection

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** How do plugins contribute dockable panels without touching window-manager code?

## toolWindow EP
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml`; platform EP in `META-INF/PlatformExtensionPoints.xml`: `<extensionPoint name="toolWindow" beanClass="com.intellij.openapi.wm.ToolWindowEP" dynamic="true"><with attribute="factoryClass" implements="com.intellij.openapi.wm.ToolWindowFactory"/></extensionPoint>`.
**Signature:** `<toolWindow id="T" anchor="bottom|right|left|top" [secondary="true|false"] [canCloseContents="true"] icon="<class>.<FIELD>" factoryClass="FQN"/>`.
**Data Shape:** id = user-visible title + registry key; anchor/secondary = initial docking; icon = class-referenced static field; the FACTORY creates content lazily on first open.

### Decisive source
```xml
<toolWindow id="Python Packages" anchor="bottom" secondary="true"
            icon="com.jetbrains.python.icons.PythonIcons.Python.PythonPackages"
            factoryClass="com.jetbrains.python.packaging.toolwindow.PyPackagesToolWindowFactory" />
<toolWindow id="Python Console" anchor="right" canCloseContents="true"
            icon="...PythonConsoleToolWindow"
            factoryClass="com.jetbrains.python.console.PythonConsoleToolWindowFactory" />
```

**Flow:** register → platform shows the strip button with icon/anchor → first activation calls factory → panel content built lazily (startup cost deferred).
**Invariant:** creation is ALWAYS behind a factory — descriptors never name content components directly, keeping startup free of tool-window instantiation. Wrong port: registering heavyweight panels that construct at boot.
**Probe:** deterministic: `grep -oE '<toolWindow [^>]*' py-plugin.xml | head -3` shows three Python panels with distinct anchors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "packages console toolwindow factory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy-factory panel registration with declarative placement; adapt docking vocabulary; omit IntelliJ tool-window state persistence. Coverage caveat: direct jar read.
