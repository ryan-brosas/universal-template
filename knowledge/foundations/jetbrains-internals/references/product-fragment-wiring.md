<!-- capsule-v2 -->
# Product fragment wiring — how an IDE product assembles itself

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214`; Codebase Memory `jetbrains-pycharm`. **Question:** How does a specific IDE product (PyCharm vs the generic Python plugin) compose platform + product-only capabilities?

## Product fragment
**Path/Symbol:** `lib/intellij.pycharm.community.jar:META-INF/PyCharmCorePlugin.xml` (auto-generated; header: "Source: org.jetbrains.intellij.build.pycharm.PyCharmCommunityProperties.getProductContentDescriptor()") + `META-INF/pycharm-core.xml`.
**Signature:** `<idea-plugin xmlns:xi=...><module value="com.intellij.modules.pycharm"/><xi:include href="/META-INF/PlatformLangPlugin.xml"/>...<content>...</content></idea-plugin>`.
**Data Shape:** `<module value="...">` grants capability tokens (e.g. `com.intellij.modules.python-core-capable`) that OTHER plugins' `<depends><plugin id=.../>` resolve against; `xi:include` pulls platform/plugin descriptors into one effective document.

### Decisive source
```xml
<!-- DO NOT EDIT: This file is auto-generated from Kotlin code -->
<idea-plugin xmlns:xi="http://www.w3.org/2001/XInclude">
  <module value="com.intellij.modules.pycharm"/>
  <module value="com.intellij.modules.python-core-capable"/>
  <xi:include href="/META-INF/PlatformLangPlugin.xml"/>
  <xi:include href="/META-INF/pycharm-core.xml"/>
  <content namespace="jetbrains">
    <module name="intellij.platform.remoteServers.impl" loading="embedded"/>
  </content>
</idea-plugin>
```
And in pycharm-core.xml — the product-vs-plugin split:
```xml
<!-- Components and extensions declared in this file work ONLY in PyCharm, not in Python plugin. Both Community and Professional editions. -->
```

**Flow:** build system generates fragment → fragment includes platform descriptor + product-only pieces → plugins depending on `com.intellij.modules.python-core-capable` activate only inside products exposing that token.
**Invariant:** capability tokens are declared by products, consumed by plugins via `<plugin id>` depends — this is how one plugin binary targets multiple IDEs with different feature sets. Wrong port: shipping product-specific extensions inside the shared plugin descriptor.
**Probe:** deterministic: `unzip -p lib/intellij.pycharm.community.jar META-INF/PyCharmCorePlugin.xml | grep 'module value'` → 4 tokens incl. python-core-capable.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "jupyter kernel intellij", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-token products (product declares features it can host; plugins declare what they require); adapt token naming; omit the Kotlin build-generation pipeline. Coverage caveat: direct jar read.
