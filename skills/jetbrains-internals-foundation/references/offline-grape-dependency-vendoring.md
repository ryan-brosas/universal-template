<!-- capsule-v2 -->
# Offline Grape vendoring — how do runtime-compiled scripts get their @Grab dependencies on an AIR-GAPPED install?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; study/reference only); Codebase Memory `jetbrains-datagrip`. **Question:** How does a scripted plugin declare Maven dependencies at runtime AND guarantee they resolve without network access?

## Graph-selected seam: per-plugin pre-vendored ivy repository
**Path/Symbol:** `plugins/grid-loader-json/grape/grapes/**` and `plugins/grid-loader-xls/grape/grapes/**` (loose trees, graph-indexed); EP `com.intellij.grid.scripting.ivyLocalRepository` declared in grid-plugin's `intellij.grid.scripting.impl` module descriptor; implementations `JsonIvyLocalRepository`/`XlsIvyLocalRepository extends BaseIvyLocalRepository`; runner side `DatabaseExtensionScriptRunnerInIde.class` strings (`grape.root`, `getEngineFor`).
**Signature:** `<extensionPoint qualifiedName="com.intellij.grid.scripting.ivyLocalRepository" interface="com.intellij.grid.scripting.impl.IvyLocalRepository" dynamic="true" />`; `BaseIvyLocalRepository.getPath()` = `PluginPathManager.getPluginResource(clazz, "grape")/<SimpleName>`.
**Data Shape:** script header declares `@Grab("group:artifact:version")`; the plugin dir vendors the FULL transitive closure as ivy layout `grape/grapes/<group>/<artifact>/{ivy-<ver>.xml, ivy-<ver>.xml.original, ivydata-<ver>.properties, jars/<artifact>-<ver>.jar}`. JSON loader: jackson-core/-databind/-annotations 2.16.1 (+bom/parent poms). XLS loader: poi 5.4.0 + poi-ooxml(-lite) + xmlbeans 5.3.0 + SparseBitSet 1.3.0 + commons-codec 1.17.1 + log4j-api 2.24.3 + jackson-bom 2.17.2.

### Decisive source
```groovy
// JSON.groovy:4-5 — runtime-declared deps...
@Grab("com.fasterxml.jackson.core:jackson-core:2.16.1")
@Grab("com.fasterxml.jackson.core:jackson-databind:2.16.1")
```
```
$ find plugins/grid-loader-json/grape -name '*.jar'   # executed (subset)
.../jackson-annotations/jars/jackson-annotations-2.16.1.jar
.../jackson-core/jars/jackson-core-2.16.1.jar
.../jackson-databind/jars/jackson-databind-2.16.1.jar
// BaseIvyLocalRepository.class strings (executed):
grape / getPluginResource / &Cannot find path to local repository
// DatabaseExtensionScriptRunnerInIde.class strings (executed):
grape.root / getEngineFor
// DataLoaderPluginsManager enum catalog (executed):
intellij.grid.loader.json | intellij.grid.loader.xls | intellij.grid.loader.parquet | intellij.grid.loader.shp
```

**Flow:** each loader plugin ships its own complete Grape cache → its one-class IvyLocalRepository implementation points the scripting kernel at `plugins/<loader>/grape` → script engine run sets `grape.root` so @Grab resolution stays inside the plugin tree (progress streamed via `setDependenciesProgressConsumer`) → resolution never leaves the install; missing repo = explicit warn ("Cannot find path to local repository"), unit-test mode has a dedicated branch.
**Invariant:** the vendored closure must be COMPLETE (pom/bom parents included — jackson-bom and junit-boms are present though unused at runtime, proving whole-repo snapshots rather than minimal sets); versions in @Grab MUST byte-match vendored ivy names or resolution fails offline. The catalog enum proves loaders are DISTRIBUTED SEPARATELY (parquet/shp listed but absent here — bundled count is exactly 2).
**Probe:** P6/P8/P9 outputs quoted above; `ls plugins | grep -c '^grid-loader-'` → 2 (executed 2026-08-25).
**Coverage caveat:** grape ivy XMLs ARE loose/indexed; the kernel classes are jar-side direct extraction pinned to build 262.9437.163.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "extractMapRow consumeColumns schema", limit: 8 });
```
(Same-script neighborhood; grape ivy files surface as graph Class nodes, e.g. jackson-base ivy-2.16.1.xml:132.)

## Verdict
Adopt: vendor-the-whole-Grape-tree-inside-the-plugin + per-plugin repository EP + engine-level root override — the general shape for any runtime-compiling plugin host that must work air-gapped. Adapt ivy specifics to your resolver. Omit exact dependency pins (they track the train). Pairs with grid-loader-script-contract; explains why loader plugins stay tiny jars with big sibling directories.