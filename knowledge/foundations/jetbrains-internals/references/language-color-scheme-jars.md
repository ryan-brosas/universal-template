<!-- capsule-v2 -->
# Language color-scheme jars — how does a language plugin ship its highlight palette?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** Where do per-language syntax colors ship, and what is the minimal file contract a new language plugin must meet?

## Connected graph-selected seam
**Path/Symbol:** `<language-plugin>.jar:colors/<SchemeName>.xml` + `<langPackage>/colors/highlighterDemoText.<ext>` — decisive instance `plugins/sh-plugin/lib/intellij.sh.core.jar:colors/ShDarcula.xml`, `colors/ShDefault.xml`; toml rides `org/toml/ide/colors/highlighterDemoText.toml` INSIDE its code package; cwm carries `colors/dark_attributes.xml`+`light_attributes.xml` in a module jar.
**Signature:** n/a (resource plane).
**Data Shape:** scheme XML = `<list>` of `<option name="TOKEN.KEY">` entries, each a `<value>` with optional `FOREGROUND`/`BACKGROUND` (6-hex, NO leading #) and `FONT_TYPE` (`1`=bold). Missing tokens fall through to the base theme. The demo text is the SAME language source with `<COMMENT>`, `<KEY>`, `<STRING>` wrappers marking spans for the settings preview.

### Decisive source
```xml
<!-- ShDarcula.xml, first entry verbatim -->
<list>
    <option name="BASH.EXTERNAL_COMMAND">
        <value>
            <option name="FOREGROUND" value="c57633"/>
        </value>
    </option>
```
```
$ unzip -p plugins/toml/lib/intellij.toml.core.jar org/toml/ide/colors/highlighterDemoText.toml | head -1
<COMMENT># This is a TOML document.</COMMENT>

<KEY>title</KEY> = <STRING>"TOML Example"</STRING>
```

**Flow:** plugin jar ships `colors/*.xml` per bundled scheme → EditorColorsManager loads them as page-2 overlays over the platform base → settings preview renders highlighterDemoText with token tags mapping each span back to a scheme key.
**Invariant:** colors are hex WITHOUT '#' (one 5-digit value `b0c95` exists — the grammar is hex-string, not fixed-width) and keys are UPPERCASE_DOT token names owned by the language's highlighter — a porter reusing ids across languages breaks silently because matching is by exact token key. Delta-only files are legitimate and tiny: ShDefault.xml = 6 token keys (4 FOREGROUND + 1 FONT_TYPE + 1 BACKGROUND), ShDarcula.xml = 5 token keys (1 FOREGROUND + 3 FONT_TYPE + 1 BACKGROUND).
**Probe:** from pycharm install root:
`unzip -p plugins/sh-plugin/lib/intellij.sh.core.jar colors/ShDarcula.xml | grep -o 'option name' | wc -l` prints `10` (5 token keys × 2 option tags each);
`unzip -p plugins/sh-plugin/lib/intellij.sh.core.jar colors/ShDefault.xml | grep -c 'BASH\.'` prints `6` (token keys in the light twin);
`unzip -p plugins/toml/lib/intellij.toml.core.jar org/toml/ide/colors/highlighterDemoText.toml | head -c 60` starts `<COMMENT>`.
Cluster census: only sh/toml/cwm ship this plane cluster-wide (5 non-class data files total outside qodana.jar) — most languages inherit entirely from theme-metadata + expui defaults.
**Coverage caveat:** jar resource plane unindexed; unzip probes are the primitive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "editor colors textAttributesKey language", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: per-language delta color files + tagged demo-text preview as the minimal palette contract; extends theme-metadata-contract ([DONE:248] group) which owns the NAMED-COLOR vocabulary side. Adapt: token-key naming and hex grammar to your host. Omit: IntelliJ EditorColorsManager load order.
