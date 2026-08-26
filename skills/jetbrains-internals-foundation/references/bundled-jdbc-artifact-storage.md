<!-- capsule-v2 -->
# database-artifactsBundle — how do you ship JDBC drivers INSIDE the install so offline machines can still connect?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; study/reference only); Codebase Memory `jetbrains-datagrip`. **Question:** What is the minimal plugin shape that turns a directory of driver zips into a first-class, version-resolved LOCAL artifact source beside the usual download path?

## Graph-selected seam: bundled-driver storage EP stack
**Path/Symbol:** `plugins/database-artifactsBundle/lib/database-artifactsBundle.jar:META-INF/plugin.xml` + `com/intellij/database/artifactsBundle/{ArtifactsBundleStorage, ArtifactsBundleMacroContributor, ArtifactsBundleStartupActivity}.class`; data plane `plugins/database-artifactsBundle/artifacts/<Driver Name>/<version>.zip`.
**Signature:** `ArtifactsBundleStorage implements com.intellij.database.dataSource.artifacts.LocalArtifactStorage` — `resolve(artifactId: String, Version): Path` = `getBundleDir().resolve(findArchive(dir, Version))`; macro contributor registers `DB_ARTIFACTS_BUNDLE -> artifacts/`.
**Data Shape:** five bundles shipped: MongoDB/1.21.zip, MySQL ConnectorJ/9.5.0.zip, PostgreSQL/42.7.3.zip, Redis/1.6.zip, SQL Server/13.2.1.zip (~49 MB). Directory name carries display name, zip name carries version; a `(String, Version)->Version` comparator parses dir-name versions.

### Decisive source
```xml
<idea-plugin>
  <id>intellij.database.artifactsBundle</id>
  <name>Database Bundled Drivers</name>
  <dependencies>
    <module name="intellij.database" />
    <module name="intellij.database.connectivity" />
    <module name="intellij.database.core.impl" />
  </dependencies>
  <extensions defaultExtensionNs="com.intellij">
    <pathMacroContributor implementation="...ArtifactsBundleMacroContributor" />
    <database.localArtifactStorage implementation="...ArtifactsBundleStorage" />
    <postStartupActivity implementation="...ArtifactsBundleStartupActivity" />
  </extensions>
</idea-plugin>
```
```
$ find plugins/database-artifactsBundle/artifacts -name '*.zip' | sort   # executed
artifacts/MongoDB/1.21.zip
artifacts/MySQL ConnectorJ/9.5.0.zip
artifacts/PostgreSQL/42.7.3.zip
artifacts/Redis/1.6.zip
artifacts/SQL Server/13.2.1.zip
$ strings ArtifactsBundleMacroContributor.class | grep '^DB_ARTIFACTS_BUNDLE$'   # executed
DB_ARTIFACTS_BUNDLE
```

**Flow:** descriptor wires three extensions → macro contributor publishes the `$DB_ARTIFACTS_BUNDLE` path macro pointing at `artifacts/` (data-source XML can reference drivers by macro without absolute paths) → LocalArtifactStorage resolves (artifactId, requested Version) against the tree, choosing best matching versioned zip → postStartup ProjectActivity reconciles DatabaseArtifactManager/Loader state so bundled artifacts appear WITHOUT user action.
**Invariant:** the download pipeline is NOT replaced — this is an additional local SOURCE keyed into the existing artifact-resolution SPI; resolution must be version-aware (dir-name parsing) and fail-soft when no archive matches (`exists()` check present in strings). Startup activity is a coroutine `ProjectActivity`, consistent with the startup-activity-ladder background rung.
**Probe:** P3/P4 outputs quoted above (executed 2026-08-25); `unzip -p database-artifactsBundle.jar META-INF/plugin.xml` excerpt byte-matches descriptor on disk.
**Coverage caveat:** jar classes are indexer-skipped BY DESIGN — evidence via direct extraction pinned to build 262.9437.163; artifact zips untracked by graph (not_tracked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "data loader import export", limit: 10 });
```
(Loose-file plane anchor for the same lane; the bundle plane itself has no indexed symbols — see caveat.)

## Verdict
Adopt: versioned-zip-tree + path-macro + local-storage-EP + startup-reconciliation as the OFFLINE driver-provisioning pattern. Adapt macro naming and storage SPI to your host. Omit per-vendor driver internals. Distinct from dependency-support-registry (that declares ecosystem coordinates for DETECTION; this ships the actual binaries). Next-pass: cloudExplorer plugins may add credential-side counterparts.