<!-- capsule-v2 -->
# themeMetadata contract — how does a feature expose its UI keys for theming without shipping a theme?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-rider`. **Question:** How do plugin-specific colors become first-class citizens of the IDE's theme system (editable in theme editor, overridable by any theme) while the plugin itself ships zero styling?

## Metadata-only theme surface
**Path/Symbol:** `lib/intellij.profiler.common.jar!META-INF/CommonProfilerPlugin.themeMetadata.json`.
**Signature:** `{"name": "<pluginThemeName>", "fixed": false, "ui": [{"key": "Profiler.ChartSlider.foreground", "description": "...", "source": "", "since": "2023.2"}, ...]}`.
**Data Shape:** 207 `*.themeMetadata.json` across 12 products (rider 36, clion/goland/phpstorm 16 each — profiler-common shared). Keys are dot-namespaced by feature (`Profiler.*`), each entry = key + human description + since-version. `"fixed": true` would mark unthemeable keys. NO colors are specified here — only the vocabulary.

### Decisive source
```json
{
  "name": "CommonProfilerPlugin",
  "fixed": false,
  "ui": [
    {
      "key": "Profiler.ChartSlider.foreground",
      "description": "Foreground color for text attached to the chart slider (percentages and timestamp)",
      "source": "",
      "since": "2023.2"
    },
    {
      "key": "Profiler.CpuChart.background",
      "description": "Color of the area under the active CPU line chart",
      "source": "",
      "since": "2023.2"
    }
  ]
}
```

**Flow:** code paints with named keys via `JBColor.namedColor("Profiler.CpuChart.background", fallback)` → metadata declares those keys exist → platform theme editor lists them (with description + since) → third-party `.theme.json` files may override values; if none does, the in-code fallback applies.
**Invariant:** every `namedColor` key used in code MUST appear in the metadata or it is invisible/unthemeable — the JSON is a schema over code constants, and drift between them is silent. Wrong port: hardcoding RGB values in plugin code (breaks dark variants + user themes).
**Probe:** `unzip -p rider/lib/intellij.profiler.common.jar META-INF/CommonProfilerPlugin.themeMetadata.json | grep -c '"key"'` → 40+; census `for j in lib/*.jar plugins/*/lib/*.jar: unzip -l | grep -c themeMetadata.json` reproduces 207 cluster-wide.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "namedColor JBColor theme key", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: features declare themeable-key vocabularies as data; themes consume vocabularies; code keeps only fallbacks. Adapt to your host's design-token system. Omit actual color values (they live in themes + code fallbacks). Companion to pass-2 tips-and-help-surface (colors/ dirs) — that capsule covers shipped theme data, this one the declaration contract.
