<!-- capsule-v2 -->
# pluginExternalResources.unpackToPlugin — how does one plugin contribute loose resource files into ANOTHER plugin's namespace?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; platform XML Apache-2.0-marked); Codebase Memory `jetbrains-datagrip`. **Question:** How do bundled resources get registered under a DIFFERENT plugin's extension namespace so the host can consume them as its own?

## Graph-selected seam: cross-plugin loose-resource plane
**Path/Symbol:** `plugins/grid-loader-json/lib/grid-loader-json.jar:META-INF/plugin.xml:9-14` declaring EP `com.intellij.pluginExternalResources.unpackToPlugin`; platform consumers `com.intellij.ide.extensionResources.ExternalResourcesUnpackExtensionBean` + `ExtensionsRootType` (in `lib/intellij.platform.lang.impl.jar`). Resulting disk layout: `plugins/grid-loader-json/external-extensions/com.intellij.database/data/loaders/JSON.groovy`.
**Signature:** `<pluginExternalResources.unpackToPlugin unpackTo="<host-plugin-id>" />`; resolution API (class strings): `findExtensionsDirectoryImpl(PluginId, String, boolean): Path`, `getBundledExtensionsResources(PluginId, String): List<Path>`, root type key `root.type.extensions`.
**Data Shape:** one bean per declaring plugin: (declaring descriptor, unpackTo target id). Consumer filters all plugins whose descriptor id equals `unpackTo` (`ContainerUtil.filter` over `PluginDescriptor.getPluginId()`) and resolves their `external-extensions/<unpackTo>/...` subtrees as the TARGET plugin's resources.

### Decisive source
```xml
<!-- grid-loader-json.jar:META-INF/plugin.xml -->
<dependencies>
    <module name="intellij.grid.scripting.impl" />
</dependencies>
...
<extensions defaultExtensionNs="com.intellij">
    <pluginExternalResources.unpackToPlugin unpackTo="com.intellij.database" />
    <grid.scripting.ivyLocalRepository implementation="com.intellij.grid.loader.json.JsonIvyLocalRepository" />
</extensions>
```
```
// ExternalResourcesUnpackExtensionBean.class strings (executed):
3com.intellij.pluginExternalResources.unpackToPlugin   <- literal EP name
// ExtensionsRootType.class strings: root.type.extensions,
// findExtensionImpl / findExtensionsDirectoryImpl / getBundledExtensionsResources
```

**Flow:** tiny loader plugin declares its loose tree "belongs to com.intellij.database" → platform enumerates all descriptors carrying the EP, keeps those matching the target id → exposes the subtree through the extensions root-type API so host code queries resources BY ITS OWN plugin id → host-side scripting kernel discovers `*/data/loaders/*.groovy` without knowing which contributor shipped them.
**Invariant:** the loose directory name after `external-extensions/` MUST equal the `unpackTo` value (namespace mirroring); the declaring plugin stays resolvable/dynamic while the RESOURCES are addressed as the host's. This decouples "who ships a capability" from "whose API it extends" — layered products can add formats without touching the host plugin.
**Probe:** `unzip -p plugins/grid-loader-json/lib/grid-loader-json.jar META-INF/plugin.xml | grep -nE 'unpackToPlugin|module name'` → lines 9/13 as quoted; `strings .../ExternalResourcesUnpackExtensionBean.class | grep pluginExternalResources` → EP literal. (Executed 2026-08-25.)
**Coverage caveat:** jar internals are BY-DESIGN skipped by the indexer (`check_index_coverage` on the jar: status no_recorded_issue/freshness not_tracked, recommended read_source_and_reindex) — evidence is direct extraction, pinned to build 262.9437.163. Unpack TIMING (copy vs in-place read) not traced; only the resolution surface is claimed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-datagrip", paths: ["plugins/grid-loader-json/external-extensions/com.intellij.database/data/loaders/JSON.groovy"] });
```
→ status partial (parse_partial 1-160), freshness metadata_match — the loose-file side IS indexed; the jar side is not.

## Verdict
Adopt: declare-contributor-resources-into-host-namespace EP + directory-mirrors-host-id convention — ports cleanly to any plugin registry that resolves loose resources by owner id. Adapt root-type key naming to your platform. Omit IntelliJ unpack lifecycle details (not decisively evidenced here). Distinct from optional-depends-capability-fragment (that gates CODE fragments by host presence) — this moves RESOURCES across namespaces while keeping the contributor independent.