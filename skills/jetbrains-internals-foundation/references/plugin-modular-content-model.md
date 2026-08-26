<!-- capsule-v2 -->
# Plugin modular content model — v2 modules with embedded descriptors

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** How do modern plugins split into modules without shipping one XML per module?

## Content-module layout
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (2,241 lines; `<content namespace="jetbrains">` with 377 module tags; 109 EPs; 106 localInspections).
**Signature:** `<content namespace="jetbrains"><module name="intellij.python.parser" loading="required"><![CDATA[<idea-plugin>...</idea-plugin>]]></module>...</content>`.
**Data Shape:** each `<module>` embeds a COMPLETE descriptor as CDATA — its own dependencies, extensionPoints, extensions; attributes: `loading="required|optional|embedded"`, `visibility="public|internal|private"` (29 internal / 21 public / 2 private in this plugin).

### Decisive source
```xml
<module name="intellij.python.parser" loading="required"><![CDATA[<idea-plugin visibility="public">
  <extensions defaultExtensionNs="com.intellij">
    <fileType name="Python" language="Python" extensions="py;pyw" hashBangs="python"
              implementationClass="com.jetbrains.python.PythonFileType" fieldName="INSTANCE" />
  </extensions>
  <extensionPoints>
    <extensionPoint qualifiedName="Pythonid.dialectsTokenSetContributor" ... dynamic="true" />
  </extensionPoints>
</idea-plugin>]]></module>
```

**Flow:** outer descriptor declares id/version/dependencies → content modules each carry self-contained capability slices → loader parses embedded descriptors when the module loads (required eagerly, optional on demand).
**Invariant:** an embedded descriptor is a full `<idea-plugin>` document — it can declare its own EPs and consume others' via namespaces; module names are dependency targets for other modules' `<dependencies><module name=.../>`. Wrong port: treating CDATA as documentation or stripping per-module visibility.
**Probe:** deterministic: `unzip -p plugins/python-ce/lib/*.jar META-INF/plugin.xml | grep -c '<extensionPoint'` → 91 top-level + more inside CDATA (109 total); `grep -c '<localInspection'` → 106.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "python console pydev", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-file modular manifests (one distribution artifact, many loadable capability slices) for any plugin system; adapt loading/visibility vocabulary; omit JetBrains build-tooling that generates these files. Coverage caveat: direct jar read.
