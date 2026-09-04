<!-- capsule-v2 -->
# pluginIcon convention — how does a bundled plugin expose its marketplace-style identity?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-clion`. **Question:** What icon assets must every plugin jar carry and what do the naming variants encode?

## META-INF/pluginIcon.svg (+_dark)
**Path/Symbol:** `<any plugin jar>!META-INF/pluginIcon.svg` and `META-INF/pluginIcon_dark.svg`.
**Signature:** fixed member paths — no configuration, discovery is by convention at `META-INF/pluginIcon{,_dark}.svg`.
**Data Shape:** cluster census 741 light + 371 dark across 13 products — roughly HALF the plugins bother with the dark variant (the platform falls back to the light SVG with its own recoloring when `_dark` is absent). restClient.jar carries only `pluginIcon.svg`; product-level icons live in the app icon set, not in jars. 40×40 SVG is the expected geometry for bundled/marketplace parity.

### Decisive source
```
restClient.jar
  META-INF/pluginIcon.svg          (present)
  META-INF/pluginIcon_dark.svg     (ABSENT -> platform fallback: recolored light variant)

# cluster census
pluginIcon.svg       741   (every plugin that wants an identity)
pluginIcon_dark.svg  371   (~50% opt-in; absence degrades gracefully)
```

**Flow:** platform lists installed/bundled plugins → reads `META-INF/pluginIcon.svg` from each jar's classpath → Settings/marketplace UI renders it → on dark themes, `pluginIcon_dark.svg` if present, else automatic luminance-based recolor of the light asset.
**Invariant:** identity-by-convention means NO registration line exists to get wrong — but the path is case-sensitive and fixed; renaming breaks it silently (icon just disappears). The dark-variant gap is tolerated BY DESIGN via recolor fallback.
**Probe:** `unzip -l clion/plugins/restClient/lib/restClient.jar | grep -c pluginIcon` → 1; cluster loop counting both names across plugins/*/lib/*.jar reproduces 741/371.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "plugin icon loader classpath svg", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt convention-over-configuration asset discovery with graceful theme fallback; adapt geometry/format to your host. Omit per-product icon catalogs (pattern captured here). Pass-4 adjudication of round-2 probe: real convention, now captured.
