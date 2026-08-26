<!-- capsule-v2 -->
# File-type registration contract — singleton reuse without implementation

**Source:** JetBrains IDE installed builds `PyCharm 262.9437.214` / `Rider 262.8665.400`; Codebase Memory `jetbrains-pycharm`, `jetbrains-rider`. **Question:** How do you register a file type, and how can a plugin EXTEND an existing type it does not own?

## fileType extension
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (intellij.python.parser module) + `plugins/rider-unity/lib/rider-plugins-unity.jar:META-INF/plugin.xml` (backend module).
**Signature:** `<fileType name="T" [language="L"] extensions="a;b" [hashBangs="..."] [implementationClass="FQN"] [fieldName="INSTANCE"]/>`.
**Data Shape:** name = registry key; extensions = `;`-separated; language binds editor seams; implementationClass+fieldName = class-held singleton instance. Omitting implementationClass RE-USES the existing registered type under that name.

### Decisive source
```xml
<!-- owner: full declaration with singleton field -->
<fileType name="Python" language="Python" extensions="py;pyw" hashBangs="python"
          implementationClass="com.jetbrains.python.PythonFileType" fieldName="INSTANCE" />
<!-- extender: same name, NO implementationClass — adds extensions to ShaderLab -->
<fileType name="ShaderLab" fieldName="INSTANCE" implementationClass="...ShaderLabFileType"
          language="ShaderLab" extensions="shader" />
<fileType name="HLSL" extensions="cg;cginc;hlslinc;compute;urtshader" />
```

**Flow:** first plugin declares the type (impl + default extensions) → later plugins re-declare `<fileType name="<existing>">` with only extra attributes → container merges (adds extensions) instead of duplicating.
**Invariant:** exactly ONE implementationClass per name across all contributors; extenders must not re-declare it. Wrong port: copying the impl class reference into the extension tag (duplicate registration), or inventing a new name and breaking "open by content/shebang" resolution.
**Probe:** deterministic: `unzip -p rider-plugins-unity.jar META-INF/plugin.xml | grep '<fileType name="HLSL"'` → attribute-only tag.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "unity shader debugger rider backend", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt name-keyed file-type registry with merge-on-redeclare; adapt extension binding to your host's file model; omit IntelliJ's FileTypeManager conflict-resolution internals. Coverage caveat: direct jar read.
