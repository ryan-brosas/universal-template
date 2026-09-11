<!-- capsule-v2 -->
# Bundled shared-index chunks — how do you ship prebuilt indexes beside a product so first open skips cold indexing?

**Source:** JetBrains GoLand installed distribution (proprietary; study/reference use only) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** what is the complete contract for bundling shared indexes as product data — declaration, naming, format, provenance?

## Two-plugin split: infrastructure core + per-language bundled payload
**Path/Symbol:** `plugins/indexing-shared/lib/indexing-shared.jar!META-INF/plugin.xml` (id `intellij.indexing.shared.core`) + `plugins/go-sharedIndexes-bundled/lib/go-sharedIndexes-bundled.jar!META-INF/plugin.xml` (id `org.jetbrains.plugins.go.sharedIndexes.bundled`, implementation-detail, depends on `org.jetbrains.plugins.go`).
**Signature:** `<sharedIndexBundled pluginPath="gosdk" />` (product side also uses `productPath=`, e.g. `productPath="jdk-shared-indexes"`).
**Data Shape:** chunk pair per corpus: `gosdk/gosdk-63c95d513abe-9addb268e56c.ijx` (ZIP container, PK magic) + sibling `.txt` = the recorded generator command line; dual hash name = corpus identity × index-format version.

### Decisive source
```xml
<!-- go-sharedIndexes-bundled.jar!META-INF/plugin.xml -->
<idea-plugin implementation-detail="true" package="com.goide.index.shared.bundled">
  <content>
    <module name="intellij.go.sharedIndexes.bundled/sharedCore"><![CDATA[
      <idea-plugin package="com.goide.index.shared.bundled.gosdk">
        <dependencies><plugin id="intellij.indexing.shared.core" /></dependencies>
        <extensions defaultExtensionNs="com.intellij">
          <sharedIndexBundled pluginPath="gosdk" />
        </extensions>
      </idea-plugin>]]></module>
  </content>
</idea-plugin>
<!-- gosdk/gosdk-63c95d513abe-9addb268e56c.txt (140 bytes, verbatim): -->
--version=1.26.0 --version=1.25.7 --additional-os=windows --additional-os=linux --additional-os=mac --generate-binary-reproducible-maps=true
```

**Flow:** generator module's `appStarter id="dump-shared-index"` (+ `sharedIndexDumpCommand` / `indexesExporterExtension` EPs) produces chunks offline → bundle dir declared via `sharedIndexBundled` → IDE discovers bundled chunks at startup and maps project SDK/library files by hash instead of indexing → network suggesters (jdk/maven `sharedIndexSuggester`, CDN registry keys, `projectConsentDecisionOverrider`) extend the same vocabulary to downloaded corpora.
**Invariant:** the `.txt` twin IS the reproducible-build recipe — data without its generation command is unverifiable, so they ship together; multi-`--version` flags prove ONE chunk dir serves several SDK versions (1.26.0 AND 1.25.7); chunk applicability rides dual-hash naming, not directory scans. Cross-product rider: `intellij.python.sharedIndexes` module ships inside this Go install behind a `com.intellij.modules.python` dependency it cannot satisfy — modules ride every install and gate themselves by dependency.
**Probe:** `unzip -p plugins/go-sharedIndexes-bundled/lib/go-sharedIndexes-bundled.jar META-INF/plugin.xml | grep -c sharedIndexBundled` → `1`; `head -c 4 …/gosdk/*.ijx | od -c | head -1` → `P K 003 004`.

## Get live surrounding code
**Retrieve:** (zero-symbol expectation for these names; coverage check recorded)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "sharedIndexBundled shared index bundled", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/go-sharedIndexes-bundled/gosdk/gosdk-63c95d513abe-9addb268e56c.txt"] });
```

## Verdict
Adopt: prebuilt-index shipping as (declared dir + dual-hash chunk + generator-provenance twin); deny-by-default consent + registry-keyed CDN for downloaded corpora. Adapt: hash scheme and dump-command surface to your indexer. Omit: JetBrains' internal chunk binary layout (opaque without generator sources).
