<!-- capsule-v2 -->
# WorkspaceModel file-index contributor plane — how does the file index learn what to index, and why do product jars declare platform-owned contributors?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How is "which files/roots belong in the index" declared as data — and what does it mean that the PYTHON descriptor declares contributors like ContentRootFileIndexContributor?

## Connected graph-selected seam
**Path/Symbol:** EP `com.intellij.workspaceModel.fileIndexContributor` (short name `fileIndexContributor` under `defaultExtensionNs` child-tag form). Declarations found: `lib/intellij.pycharm.pro.jar:META-INF/PythonPlugin.xml` ×**9** (occurrence-exact; naive `grep -c 'fileIndexContributor'` says 10 LINES — one line mentions it twice; minified-XML trap from pass 11 recurred), `plugins/javascript-plugin/lib/javascript-plugin.jar:META-INF/plugin.xml` ×7, `plugins/css-plugin/lib/css-plugin.jar:META-INF/plugin.xml` ×1.
**Signature:** `<workspaceModel.fileIndexContributor implementation="<FQN>"/>` — SINGLE-attribute form: zero `order=`, zero `id`, zero `os=` (0 order attributes verified across all 9 py declarations).
**Data Shape:** two strata by implementation package: PLATFORM CORE (declared inside PythonPlugin.xml because merged product descriptors re-declare platform EPs per ep-declaration-redundancy): ProjectRootEntityWorkspaceFileIndexContributor, AutoExcludeWorkspaceFileIndexContributor, ContentRootFileIndexContributor, SourceRootFileIndexContributor, LibraryRootFileIndexContributor, ExcludedRootFileIndexContributor, UnloadedContentRootFileIndexContributor, SdkEntityFileIndexContributor, ScratchRootsEntityWorkspaceFileIndexContributor — i.e. content/source/library/excluded/unloaded/sdk/scratch = the WHOLE root taxonomy. PRODUCT layer adds domain exclusions: NodeModulesDirectoryExclude/ExclusionPattern/LibraryEntity + YarnPnpLibrary/YarnPnpExclude + JsExclude + PackageJsonExclude (js) and CssAdditionalLibraryFileIndexContributor (css).

### Decisive source
```
$ unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml \
    | grep -o '<workspaceModel.fileIndexContributor [^>]*>' | head -4
<workspaceModel.fileIndexContributor implementation="com.intellij.workspaceModel.ide.ProjectRootEntityWorkspaceFileIndexContributor" />
<workspaceModel.fileIndexContributor implementation="com.intellij.workspaceModel.ide.AutoExcludeWorkspaceFileIndexContributor" />
<workspaceModel.core.fileIndex.impl.ContentRootFileIndexContributor" />
<workspaceModel.core.fileIndex.impl.SourceRootFileIndexContributor" />
```
(first two trimmed of long FQNs for width; full FQNs in Path/Symbol above)

**Flow:** workspace model entities (content roots, libraries, SDKs, scratches…) exist independently → each contributor maps entity→indexing behavior (include/exclude/library-kind) → the file index composes ALL contributions at refresh. Exclusion contributors are separate classes from inclusion ones (NodeModulesDirectoryExclude vs LibraryEntity pair) — exclude is a first-class declaration, not an absence.
**Invariant:** ordering between contributors is IRRELEVANT here (zero order attributes — unlike run-config or editor-action planes where order is anchor currency); correctness comes from entity-type partitioning, not sequencing. A porter who adds sequencing machinery to this EP has misread the design; one who forgets the AutoExclude contributor breaks "node_modules excluded" expectations silently.
**Probe:** from `<install>` root:
`unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -o '<workspaceModel.fileIndexContributor' | wc -l` → `9`;
`unzip -p plugins/javascript-plugin/lib/javascript-plugin.jar META-INF/plugin.xml | grep -o '<workspaceModel.fileIndexContributor' | wc -l` → `7`;
`unzip -p lib/intellij.pycharm.pro.jar META-INF/PythonPlugin.xml | grep -o 'fileIndexContributor[^>]*order=' | wc -l` → `0`.
**Coverage caveat:** declarations live in jar-resident minified XML — not graph-indexed (search_code zero); unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target for the XML plane (adjudicated wrong-plane). Deterministic retrieval:
`unzip -p <jar> META-INF/plugin.xml | grep -o 'fileIndexContributor[^ ]* implementation="[^"]*"'`.

**Complements:** ep-declaration-redundancy (why platform contributors appear in a product descriptor), index-completion-pairing (the OTHER index plane: search indexes vs this file-index membership plane), module-visibility-tiers (same descriptor, orthogonal attribute grammar).

## Verdict
Adopt: file-index membership as attribute-free entity-mapping contributions; keep include/exclude as paired contributor classes. Adapt the entity taxonomy to your model. Omit IntelliJ's workspace-entity persistence internals (not shipped as source).
