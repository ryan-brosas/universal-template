<!-- capsule-v2 -->
# Bundled-JRE tuning plane — which runtime behaviors does an install pre-decide before any app code runs?

**Source:** JetBrains Fleet install `air` 262.132.35, JetBrains Runtime `25.0.2-329.111` per `dockMetadata.json` (proprietary distribution; stock JDK files keep their headers); Codebase Memory `jetbrains-air` (`jbr/conf/jaxp.properties`: no_recorded_issue; `jbr/lib/jvm.cfg`, `jbr/lib/fonts/font.conf`: parse-partial — snippet source is ground truth). **Question:** What is the minimal set of JRE files an installer ships to pin JVM behavior for a GUI product?

## Connected graph-selected seam
**Path/Symbol:** `jbr/lib/jvm.cfg`, `jbr/conf/{jaxp,net,logging,management/management}.properties`, `jbr/lib/fonts/font.conf`, `jbr/legal/<jdk.module>/*.md`.
**Signature:** `jvm.cfg = "<variant> KNOWN|IGNORE" lines`; `font.conf` = fontconfig XML `<match target="font">` rules; conf properties = documented JDK factory/config files.
**Data Shape:** three distinct populations: (a) launcher variant gate — exactly two lines; (b) STOCK JDK configuration docs shipped verbatim (jaxp.properties documents the JAXP lookup precedence "2nd to the System Property"; net/logging/management carry no vendor modifications); (c) ONE deliberate rendering patch — font.conf.

### Decisive source
```text
$ cat jbr/lib/jvm.cfg                       # complete file (graph parse-partial 1-2)
-server KNOWN
-client IGNORE

$ cat jbr/lib/fonts/font.conf               # complete file
<fontconfig>
  <match target="font">
    <test name="family" qual="all" compare="not_eq"><string>Consolas</string></test>
    <test name="family" qual="all" compare="not_eq"><string>Noto Sans Mono CJK JP</string></test>
    <test name="size" qual="any" compare="less"><double>12</double></test>
    <test name="weight" compare="less"><const>medium</const></test>
    <edit mode="assign" name="hintstyle"><const>hintfull</const></edit>
  </match>
</fontconfig>
```
The font rule: small (<12) or lighter-than-medium text gets FULL hinting — except Consolas and Noto Sans Mono CJK JP, whose own metrics are trusted. This is an editor-legibility patch over fontconfig defaults, not a user setting.

**Flow:** launcher reads jvm.cfg to pick `-server` and refuse `-client` → JDK internals read conf/*.properties with their standard precedence (system property wins) → fontconfig applies font.conf at font-render time → jbr/legal surfaces attribution per JDK module only if queried.
**Invariant:** everything in this plane is decided BEFORE application code exists — none of it is reachable from settings or registry keys; a porter who re-derives these choices at app level ships them too late (fonts rasterize per-glyph, JVM variant is fixed at exec).
**Probe:** from install root: `cat jbr/lib/jvm.cfg` → the two lines above; `grep -ic jetbrains jbr/conf/net.properties jbr/conf/logging.properties` → `0` hits each (stock); `grep -c '<match target="font">' jbr/lib/fonts/font.conf` → `1`; `ls jbr/legal | wc -l` → `69` JDK-module dirs; `find jbr/legal -name '*.md' | wc -l` → `45` third-party notices (e.g. `java.base/{aes,cldr,icu,c-libutl,public_suffix}.md`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.jbr.lib.jvm.cfg.__file__" });
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "File", file_pattern: "jbr/(conf|lib/fonts)", detail: "ids", limit: 15 });
```

## Verdict
Adopt: ship exactly {variant gate, stock JDK configs, one targeted fontconfig patch} and treat them as pre-app constants; per-module legal notice dirs keyed by JDK module name. Adapt: hint thresholds and excluded families to your editor typography. Omit: JBR build pipeline (how these files are produced). Companion seams: fleet-bundle-catalog-signed-manifests (dockMetadata.jbrVersion pins THIS runtime), fleet-dock-modulepath-layer-lists (consumer of the chosen variant).
