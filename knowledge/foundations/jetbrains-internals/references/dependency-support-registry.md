<!-- capsule-v2 -->
# dependencySupport registry — how does a plugin claim "I handle this ecosystem package" without code?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-webstorm`. **Question:** How do plugins declare third-party ecosystem dependencies so the platform can route framework detection, notifications, and feature gating by coordinate alone?

## Declarative ecosystem-coordinate claims
**Path/Symbol:** `plugins/*/lib/*.jar!META-INF/plugin.xml` → `<dependencySupport kind="..." coordinate="..." displayName="..."/>`.
**Signature:** `<dependencySupport kind="javascript" coordinate="npm:webpack" displayName="Webpack"/>`; kinds include `javascript` (npm:), plus per-language kinds (maven:, pip:, gem: coordinates in their respective plugins).
**Data Shape:** cluster census (6 products): pycharm 16, webstorm 19, rider 23, clion 17, goland 8, phpstorm 16 declarations. Examples: `angular-plugin` → npm:@angular/core, `karma`, `nextjs`, `postcss-plugin`, `prettierJS`, webpack. One line per ecosystem package; no class, no interface — pure data.

### Decisive source
```xml
<extensions defaultExtensionNs="com.intellij">
    <dependencySupport kind="javascript" coordinate="npm:webpack" displayName="Webpack" />
    <javascript.json.schema.provider implementation="com.intellij.webpack.jsonschema.Webpack2Provider" />
</extensions>
```

**Flow:** package-manager indexers scan project deps → platform joins detected coordinates against the registry of dependencySupport claims → matching plugins light up (framework detection banners, relevant settings pages, schema activation via the enabler pattern of the json-schema capsule) → displayName supplies user-visible naming without i18n coupling.
**Invariant:** the claim is IDENTITY data, not behavior — it must carry zero logic so that detection works before any plugin classes load. Wrong port: implementing detection inside plugin activation code (chicken-and-egg: you'd need the plugin loaded to know it should load).
**Probe:** `unzip -p goland/plugins/webpack/lib/webpack.jar META-INF/plugin.xml | grep -c dependencySupport` → 1; census loop over `plugins/*/lib/*.jar!META-INF/*.xml` counting `<dependencySupport ` reproduces {pycharm:16, webstorm:19, rider:23, clion:17, goland:8}.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "dependency support coordinate detection", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declarative capability-claims keyed by ecosystem coordinates for any plugin system with lazy activation; adapt coordinate schemes (npm:/pip:/gem:) to your host. Omit JetBrains' specific indexer integrations. Pairs with json-schema-catalog-plane: the claim routes detection, the enabler consumes it.
