<!-- capsule-v2 -->
# Extension consumption namespaces — who owns the EP name?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (JavaScript plugin); Codebase Memory `jetbrains-webstorm`. **Question:** How does a plugin's `<extension>` tag resolve to the right extension-point owner, and when is a custom namespace required?

## Namespace routing
**Path/Symbol:** `plugins/javascript-plugin/lib/javascript-plugin.jar:META-INF/plugin.xml` (`<extensions defaultExtensionNs=...>` blocks; 43× com.intellij, 13× JavaScript, plus com.jetbrains/com.intellij.json/org.intellij.intelliLang/...).
**Signature:** `<extensions defaultExtensionNs="<plugin-id-or-com.intellij>"><epName attr="..."/></extensions>`.
**Data Shape:** namespace = declaring plugin id (`com.intellij` for platform); the tag name inside selects the EP within that namespace; contributions only valid if that EP is declared (or the contributor declares it in its own `<extensionPoints>`).

### Decisive source
```xml
<extensions defaultExtensionNs="JavaScript">
  <frameworkIndexingHandler implementation="..." version="17" />
</extensions>
<extensions defaultExtensionNs="com.intellij">
  <defaultLiveTemplates file="liveTemplates/javascript_testing" />
</extensions>
```

**Flow:** plugin declares EP under its own id (e.g. `JavaScript`) → consumers open an extensions block with `defaultExtensionNs="JavaScript"` → tags route by EP name into that namespace.
**Invariant:** a custom-namespace contribution is invalid unless the owning plugin declared that EP and is a dependency — declare-before-consume. Wrong port: assuming all EPs live in one global namespace; the same tag name may exist in multiple namespaces with different contracts.
**Probe:** deterministic: `unzip -p .../javascript-plugin.jar META-INF/plugin.xml | grep -oE 'defaultExtensionNs="[^"]*"' | sort | uniq -c` → 13 JavaScript / 43 com.intellij split.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "typescript language service completion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt namespace-scoped extension registries to keep capability ownership explicit; adapt namespace ids to your plugin naming; omit IntelliJ's dependency-validation machinery if your host checks ownership differently. Coverage caveat: direct jar read, not graph-indexed.
