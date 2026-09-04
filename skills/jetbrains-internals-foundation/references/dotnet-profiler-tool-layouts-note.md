<!-- capsule-v2 -->
# .NET profiler tool layouts note — dotmemory/dottrace are NOT IDE manifests

**Source:** JetBrains installed builds `dotmemory` (388M) / `dottrace` (641M) at `$REFERENCE_ROOT/reference/jetbrains/`; Codebase Memory `jetbrains-dotmemory` (5,124 nodes), `jetbrains-dottrace` (12,542). **Question:** Do the two standalone .NET profiler distributions carry IntelliJ-platform manifest patterns worth mining?

## Layout classification
**Path/Symbol:** `dotmemory/*.dll` + `*.xml` (in-place .NET XML doc-comment files: Armature.xml, Avalonia.Base.xml, AutoMapper.xml...) and `JetBrains.dotMemory.*.deps.json` / `runtimeconfig.json`; same shape in dottrace. NO `lib/*.jar`, no `META-INF/plugin.xml`, no `product-info.json` with IDE fields.
**Signature:** n/a — this is an omit record, not a contract.
**Data Shape:** deps.json/runtimeconfig.json = .NET dependency graphs; per-assembly XML = API doc comments; graph nodes are doc-comment XML structure, not capability declarations.

### Decisive source
```text
$ ls dotmemory/
Armature.Core.xml  AutoMapper.dll  Avalonia.Base.xml ...
JetBrains.dotMemory.Core.MemoryDumpConverter.runtimeconfig.json
(no bin/, lib/, plugins/, product-info.json)
```

**Flow:** classify each cluster member by layout BEFORE mining → IntelliJ-platform members (bin/lib/plugins/product-info.json) yield manifest patterns; standalone tools yield none of the target categories.
**Invariant:** the jetbrains-internals foundation covers IntelliJ-platform manifest patterns only; dotmemory/dottrace are omitted WITH REASON so a later pass does not re-enter them hunting for plugin.xml that structurally cannot exist there.
**Probe:** deterministic: `ls dotmemory | grep -c product-info.json` → 0; `unzip -l` over any dotmemory binary finds no META-INF/plugin.xml.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "memory dump converter", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph indexes their XML doc surface; nothing there answers manifest porting questions.)

## Verdict
Omit both repos from this foundation's pattern set (wrong artifact family); re-enter only if a future porting question targets .NET tool dependency-graph schemas (deps.json) as a contract.

UPDATE (2026-08-25, miner-jetbrains-dotmemory lane): that clause was EXECUTED for dotmemory — see the '.NET standalone profiler plane' capsules (dotnet-deps-json-layout-map, dotnet-runtimeconfig-rollforward-contract, dotnet-launcher-platform-detection-ladder, dual-tfm-assembly-duplication, out-of-process-helper-fleet, selfapi-embed-profiling-surface, sdk-workspace-open-traversal, avares-icon-manifest-grammar). The layout classification above stands as written; the omit verdict now applies to dotTRACE only.

**Pass-15 update (2026-08-25, miner-jetbrains-dottrace lane):** that documented re-entry door was walked through. dotTrace was mined ON ITS OWN TERMS as a standalone .NET profiler distribution — see the "Standalone .NET profilers" map group (`dottrace-ui-rid-dispatch-ladder`, `deps-json-relocated-runtime-targets` [the admitted deps.json contract], `exe-config-jetbrains-assembly-file-metadata`, `snapshot-section-storage-lifecycle`, `compact-call-tree-storage-encoding`, `jetmetadata-sstg-precomputed-catalog-plane`, `testrunner-bitness-apphost-matrix`). This note's IDE-manifest omission verdict stands unchanged; only its scope note is updated. Graph count drift: this capsule cites 12,542 nodes from its mining-time status; the live ready index at pass 15 reports 12,537.
