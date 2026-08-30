<!-- capsule-v2 -->
# Bundled JSON-schema catalog plane — how do config-file schemas ride inside the plugin that edits them?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-goland`. **Question:** How does a plugin ship validation schemas for the file types it supports, and what EP wiring activates them only for matching files?

## jsonSchemas + provider stack
**Path/Symbol:** `plugins/webpack/lib/webpack.jar!jsonSchemas/*` + `META-INF/plugin.xml` extensions.
**Signature:** `<javascript.json.schema.provider implementation="com.intellij.webpack.jsonschema.Webpack2Provider"/>` ×2 (v2, v4) under `defaultExtensionNs="com.intellij"`; `<JsonSchema.ProviderFactory implementation="...Webpack4PluginProviderRegistrar"/>` under ns `JavaScript`; `<jsonSchemaEnabler implementation="...WebpackJsonSchemaEnabler"/>` under ns `com.intellij.json`.
**Data Shape:** 135 `jsonSchemas/**/*.json` files across 9 products; webpack.jar alone carries 17 (main `webpack-schema.json`, `webpack-schema4.json`, 12 per-plugin split schemas under `webpackPlugins/{name}.json`, third-party extras). Schemas are verbatim JSON Schema drafts — no JetBrains wrapper.

### Decisive source
```xml
<extensions defaultExtensionNs="com.intellij">
    <dependencySupport kind="javascript" coordinate="npm:webpack" displayName="Webpack" />
    <javascript.json.schema.provider implementation="com.intellij.webpack.jsonschema.Webpack2Provider" />
    <javascript.json.schema.provider implementation="com.intellij.webpack.jsonschema.Webpack4Provider" />
</extensions>
<extensions defaultExtensionNs="com.intellij.json">
    <jsonSchemaEnabler implementation="com.intellij.webpack.jsonschema.WebpackJsonSchemaEnabler" />
</extensions>
<extensions defaultExtensionNs="JavaScript">
    <JsonSchema.ProviderFactory implementation="com.intellij.webpack.jsonschema.Webpack4PluginProviderRegistrar" />
</extensions>
```

**Flow:** dependencySupport flags the npm coordinate → enabler decides "this project uses webpack" → ProviderFactory resolves WHICH schema version applies (config file heuristics) → provider streams the bundled JSON from the jar classpath → platform JSON validator consumes it like a remote schema. Splitting main schema + `webpackPlugins/*.json` keeps each plugin's subschema independently addressable (`$ref` composition).
**Invariant:** three DIFFERENT namespaces must all be satisfied — porting just the schema files without the enabler/providerFactory wiring yields dead data; the schema is inert until the enabler claims the containing file.
**Probe:** `unzip -l goland/plugins/webpack/lib/webpack.jar | grep -c 'jsonSchemas/.*\.json'` → 17; `unzip -p goland/plugins/webpack/lib/webpack.jar META-INF/plugin.xml | grep -c 'schema.provider'` → 3 lines (2 impls + registrar).
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "json schema provider factory enabler", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: ship schemas as data inside the feature plugin; gate activation behind an enabler + version-resolving provider factory; declare the ecosystem coordinates that trigger it. Adapt storage (remote registry vs classpath). Omit schema contents (third-party data). Cluster census: clion/goland/phpstorm/phpstorm-light 15 each via shared webpack+plugins; dataspell/rider carry their own sets.
