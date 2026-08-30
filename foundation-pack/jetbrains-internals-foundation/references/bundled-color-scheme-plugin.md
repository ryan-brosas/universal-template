<!-- capsule-v2 -->
# Bundled color scheme plugin — how is a theme packaged as a pure-data plugin?

**Source:** JetBrains IDE distributions (proprietary distribution; plugin.xml Apache-2.0-marked); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What is the minimal complete packaging contract for a theme/skin as data-only plugin, and how do semantic token names + parent inheritance keep it small?

## Connected graph-selected seam
**Path/Symbol:** `pycharm/plugins/color-scheme-monokai/lib/color-scheme-monokai.jar` → `META-INF/plugin.xml` + `colorSchemes/monokai.xml`.
**Signature:** `<extensions defaultExtensionNs="com.intellij"><bundledColorScheme id="Monokai" path="/colorSchemes/monokai" /></extensions>` (note: path WITHOUT `.xml`).
**Data Shape:** scheme XML = `<scheme name="Monokai" parent_scheme="Darcula" version="1">` with two sections: `<colors>` (flat `name→hex`: CONSOLE_BACKGROUND_KEY, SELECTION_BACKGROUND, GUTTER_BACKGROUND…) and `<attributes>` (per-text-attribute `<option name="CLASS_REFERENCE"><value><option name="FOREGROUND" value="A6E22E"/><option name="EFFECT_TYPE" value="1"/>…`). Inheritance: `<option baseAttributes="TEXT" name="CLASS_NAME_ATTRIBUTES"/>` delegates a whole attribute to its parent's definition. 53KB total for a full theme. Jar = exactly 3 entries: plugin.xml + scheme + compressed `__index__`.

### Decisive source
```xml
<bundledColorScheme id="Monokai" path="/colorSchemes/monokai" />
```
```xml
<scheme name="Monokai" parent_scheme="Darcula" version="1">
  <colors><option name="CARET_COLOR" value="F8F8F0" /></colors>
  <attributes>
    <option baseAttributes="TEXT" name="CLASS_NAME_ATTRIBUTES" />
    <option name="COFFEESCRIPT.BAD_CHARACTER"><value>…</value></option>
```

**Flow:** EP registers the scheme by id+path → loader resolves `/colorSchemes/monokai.xml` on the plugin classloader → unknown attribute namespaces (`COFFEESCRIPT.*`) ride along harmlessly for IDEs that have that language → missing attributes fall back to `parent_scheme` → `baseAttributes` delegates single attributes.
**Invariant:** the file never redefines what Darcula already colors; theme size stays proportional to the DELTA from the parent. `path` attribute omits the extension — appending `.xml` in the descriptor breaks resolution.
**Probe:** `unzip -p plugins/color-scheme-monokai/lib/color-scheme-monokai.jar colorSchemes/monokai.xml | head -1` → `<scheme name="Monokai" parent_scheme="Darcula" version="1">`; jar entry count == 3.
**Coverage caveat:** resource plane, direct extraction; no symbol index.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "color scheme editor colors load scheme", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: delta-over-parent theming, id/path EP registration without extension suffix, semantic token keys with dotted vendor namespaces, baseAttributes delegation. Adapt token vocabulary to your host editor model. Omit the Monokai palette itself. Same pattern verified across the cluster: every `plugins/color-scheme-*` dir ships this exact 3-entry shape.
