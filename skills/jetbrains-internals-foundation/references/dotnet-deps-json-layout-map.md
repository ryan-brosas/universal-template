<!-- capsule-v2 -->
# .NET deps.json as authored layout map — where does a shipped tool say its assemblies live?

**Source:** JetBrains dotMemory standalone install (proprietary distribution; not git-managed — pinned by install self-hash `41e6f647…`, graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** How does a shipped .NET tool declare assembly/native locations when deps.json is NOT a NuGet restore output?

## Standalone.Avalonia.deps.json
**Path/Symbol:** `JetBrains.dotMemory.Standalone.Avalonia.deps.json` (1,534 lines); same shape ×4 (`JetBrains.dotMemory.Core.MemoryDumpConverter{,.x86,Test}.deps.json` md5-identical `a192fb74…`).
**Signature:** `{runtimeTarget:{name:".NETCoreApp,Version=v8.0"}}, targets:{"<tfm>":{"<Package>/1":{runtimeTargets:{path:{rid,assetType,assemblyVersion,fileVersion}}}}}, libraries:{"<Package>/1":{type:"package",serviceable:true,sha512:""}}`.
**Data Shape:** every package key is VERSIONLESS (`AutoMapper/1`, `System.Text.Json/1`); 104 target paths under `NetCore/` (`rid:"any"`, managed) + 9 under `runtimes/<rid>/native`; libraries section carries blanked `sha512:""`. Declared RID matrix is a SUPERSET of disk: 10 leveldb RID variants declared while only `runtimes/linux-x64/native/libleveldb.so` materializes.

### Decisive source
```json
"runtimeTarget": { "name": ".NETCoreApp,Version=v8.0", "signature": "" },
"targets": { ".NETCoreApp,Version=v8.0": {
  "AutoMapper/1": { "runtimeTargets": { "NetCore/AutoMapper.dll":
    { "rid": "any", "assetType": "runtime", "assemblyVersion": "10.0.0.0", "fileVersion": "10.1.1.0" } } },
  ...
  "JetBrains.Platform.Lib.LibLevelDb.linux-x64.release/1": { "runtimeTargets":
    { "runtimes/linux-x64/native/libleveldb.so": { "rid": "linux-x64", "assetType": "native" } } },
  ...
"libraries": { ..., "System.Text.Json/1": { "type": "package", "serviceable": true, "sha512": "" } }
```

**Flow:** hostfxr reads deps.json -> resolves each `<Package>/1` -> loads managed assets from declared path (`NetCore/…`) and native assets from `runtimes/<rid>/native/…`; missing RIDs on disk simply never resolve on that platform.
**Invariant:** this file is an AUTHORED LAYOUT MAP: versions flattened to literal `/1`, hashes blanked, full RID matrix declared regardless of what packaging kept. Never parse it for versions/hashes or treat unmaterialized RID entries as errors.
**Probe:** `grep -o '"rid": "[^"]*"' JetBrains.dotMemory.Standalone.Avalonia.deps.json | sort | uniq -c` → `88 any / 8 unix / 8 win / 3 win-arm64|win-x64|win-x86 / 1 each linux-* osx-*` (executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "dump converter snapshot runtimeconfig", limit: 5 });
```
Caveat: the graph indexes the XML-doc plane (returns `JetBrains.Profiler.Snapshot.doc` etc.); the deps.json contract itself is direct-read only.

## Verdict
Adopt deps.json as the single layout authority with versionless package keys when you ship a flattened tool distribution; adapt the NetCore/ remap convention to your own subfolder name; omit the JetBrains LibLevelDb platform-package naming ladder unless you also declare per-RID native forks.
