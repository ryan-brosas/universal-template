<!-- capsule-v2 -->
# Bundled precomputed shared indexes — how does an IDE ship ready-made SDK indexes so a first-open project skips indexing, and what contract binds the payload to the plugin?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84` (proprietary distribution; study/reference use only). Codebase Memory `jetbrains-dataspell` (non-git install; pin = product-info.json buildNumber). **Question:** Where do bundled shared indexes live, how does the platform discover them without code, and what stops a porter from treating the `.txt` sidecar as documentation?

## Descriptor-only implementation-detail plugin + sibling payload dir
**Path/Symbol:** `plugins/pycharm-ds-sharedIndexes-bundled/lib/pycharm-ds-sharedIndexes-bundled.jar:META-INF/plugin.xml` — whole file is 659 bytes; payload lives OUTSIDE the jar at `plugins/pycharm-ds-sharedIndexes-bundled/python-sdk/`.
**Signature:** `<idea-plugin implementation-detail="true"> … <sharedIndexBundled pluginPath="python-sdk" /> </idea-plugin>` with `<depends>com.intellij.modules.dataspell</depends>` + `<depends>intellij.indexing.shared.core</depends>`.
**Data Shape:** payload = one 322,938,847-byte compiled index `python-sdk-47db7740811c-7604a7d53f56.ijx` plus a 5,602-byte single-line manifest `python-sdk-47db7740811c-7604a7d53f56.txt`; the jar itself contains ONLY the descriptor + `__index__` marker — zero classes.

### Decisive source
```xml
<idea-plugin implementation-detail="true">
  <name>Shared Indexes for Python</name>
  <id>com.jetbrains.pycharm.ds.sharedIndexes.bundled</id>
  <description><![CDATA[Shared indexes for Python interpreter files. They're intended to speed-up opening of an unindexed project.]]></description>
  <depends>com.intellij.modules.dataspell</depends>
  <depends>intellij.indexing.shared.core</depends>
  <extensions defaultExtensionNs="com.intellij">
    <sharedIndexBundled pluginPath="python-sdk" />
  </extensions>
</idea-plugin>
```

**Flow:** build precomputes SDK/stdlib/skeleton indexes on CI → drops the compiled `.ijx` beside a descriptor-only plugin dir → the single `sharedIndexBundled` extension hands the RELATIVE payload dir name (`pluginPath="python-sdk"`) to the indexing.shared.core host → at first open of a project whose interpreter matches, the host consumes the bundled index instead of cold-indexing.
**Invariant:** the manifest `.txt` is NOT human docs — its entire content is the generation command line that produced the `.ijx` (`--root=<CI path>/Python-<ver>.final.0-stdlib-<OS>-<arch>.zip` repeated per interpreter, `… --sdkMode=true --additional-os=windows --additional-os=linux --additional-os=mac --generate-binary-reproducible-maps=true`). The stem pair (`47db7740811c` content id + `7604a7d53f56`) ties `.ijx` and `.txt` together; renaming or editing either side silently orphans the bundle. `implementation-detail="true"` keeps it out of user-facing plugin UI; the product-module `<depends>` scopes it to this IDE only.
**Family:** companion capsule `shared-index-bundled-chunks` (GoLand GO-262 lane) owns the PAYLOAD interior — two-plugin core/payload split, chunk naming, index format, provenance stamps. This capsule owns the DataSpell DS-261 DECLARATION side: descriptor-only plugin, one-extension discovery, payload-dir binding, manifest-as-generation-command. Read both before porting.

**Probe:** from the install root (pins discovery-by-one-extension and manifest-as-command):
```bash
cd $REFERENCE_ROOT/dataspell && unzip -p plugins/pycharm-ds-sharedIndexes-bundled/lib/pycharm-ds-sharedIndexes-bundled.jar META-INF/plugin.xml | grep -c 'sharedIndexBundled'   # -> 1
grep -o -- '--sdkMode=true' plugins/pycharm-ds-sharedIndexes-bundled/python-sdk/python-sdk-*.txt | wc -l          # -> 1 (flag sits at END of the 5,602-byte single-line manifest; head-truncation probes read zero)
ls -l plugins/pycharm-ds-sharedIndexes-bundled/python-sdk/*.ijx | awk '{print $5}'                               # -> 322938847
```

## Get live surrounding code
Jar/descriptor planes are not symbol-indexed; Retrieve is a deterministic unzip probe:
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/pycharm-ds-sharedIndexes-bundled/python-sdk"] }); // scope check: payload intentionally outside graph
await tools.bash({ command: "cd $REFERENCE_ROOT/dataspell && unzip -p plugins/pycharm-ds-sharedIndexes-bundled/lib/pycharm-ds-sharedIndexes-bundled.jar META-INF/plugin.xml" });
```

## Verdict
Adopt the shape: capability data ships as a descriptor-only `implementation-detail` plugin whose single extension names a sibling payload directory — no loader code, pure convention. Adapt `sharedIndexBundled`/`intellij.indexing.shared.core` names to your host's index-consumer EP. Omit shipping 322MB of third-party interpreter indexes in your repo; keep the manifest-as-generation-command idea (provenance + reproducibility) for any large derived artifact. Coverage caveat: payload dir is graph-excluded by design; all claims here are direct-read evidence.
