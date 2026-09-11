<!-- capsule-v2 -->
# Settings configurable tree — parent/groupId composition with instance/bundle split

**Source:** JetBrains IDE installed builds `PyCharm 262.9437.214` / `Rider 262.8665.400`; Codebase Memory `jetbrains-pycharm`, `jetbrains-rider`. **Question:** How do settings pages register into a navigable tree without hard-coding page hierarchy in code?

## Configurable EPs
**Path/Symbol:** `lib/intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` (`projectConfigurable` / `applicationConfigurable` beanClass=`com.intellij.openapi.options.ConfigurableEP`, `<with attribute="instance" implements="com.intellij.openapi.options.Configurable"/>`) + usage in PythonCore/Rider-Unity plugin.xml.
**Signature:** `<[application|project]Configurable [parentId="P"|groupId="G"] id="X" instance="FQN" bundle="messages.B" key="k" [nonDefaultProject="true"] [groupWeight="-120"]/>`.
**Data Shape:** two anchoring modes: `parentId` = explicit parent page id; `groupId` = semantic bucket (language/tools/project.propDebugger) resolved by the platform; bundle+key externalize the label; `nonDefaultProject` marks per-project-only settings.

### Decisive source
```xml
<!-- platform EP declaration (with-contract) -->
<extensionPoint name="applicationConfigurable" dynamic="true"
                beanClass="com.intellij.openapi.options.ConfigurableEP">
  <with attribute="instance" implements="com.intellij.openapi.options.Configurable"/>
</extensionPoint>
<!-- consumers -->
<applicationConfigurable groupId="tools" instance="...PythonDocumentationConfigurable"
                         id="com.jetbrains.python.documentation.PythonDocumentationConfigurable"
                         key="external.documentation.python.plugin" />
<applicationConfigurable parentId="preferences.build.unityPlugin" id="preferences.build.unityPlugin.profiler" ... />
```

**Flow:** pages declare themselves with either parent or group → container assembles the settings tree at read time → ids double as deep-link keys (preferences.<path>).
**Invariant:** a page must be addressable by its `id`; hierarchy is DATA not code — reordering the tree never recompiles anything. Wrong port: nesting via constructor calls or assuming groupId pages need parents declared first.
**Probe:** deterministic: `grep -c 'Configurable' py-plugin.xml` shows both application and project scopes coexisting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "code style python settings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declarative two-mode settings trees; adapt grouping vocabulary; omit IntelliJ Configurable lifecycle. Coverage caveat: direct jar read.
