<!-- capsule-v2 -->
# Relocated deps.json runtime targets — how does a shipped .NET tool declare its dependency graph when assets move out of the app root?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** What at-rest contract replaces a package registry for a self-contained .NET tool whose assemblies all live under one subdirectory?

## deps.json + runtimeconfig.json pair
**Path/Symbol:** `JetBrains.dotTrace.Viewer.deps.json` + `.runtimeconfig.json` (same pattern for Home.Shell; 21 deps.json across the install).
**Signature:** `targets[".NETCoreApp,Version=v8.0"]["<Assembly>/1"].runtimeTargets[path] = {rid, assetType, assemblyVersion, fileVersion}`.
**Data Shape:** TWO planes in one manifest — (1) managed assets map logical-name → physical path prefixed `NetCore/` with rid `any`; (2) native binaries ride the STANDARD `runtimes/<rid>/native/` plane (leveldb for linux-{arm,arm64,musl-arm64,musl-x64,x64} + osx-{arm64,x64}; leveldb + JetBrains.Platform.{NativeHooks,ComponentManager} for win-{x86,x64,arm64}). Version slots normalized to literal `/1`; 129 runtimeTargets entries = 113 relocated-managed + 16 RID-native.

### Decisive source
```json
{"AutoMapper/1": {"runtimeTargets": {"NetCore/AutoMapper.dll": {
  "rid": "any", "assetType": "runtime",
  "assemblyVersion": "10.0.0.0", "fileVersion": "10.1.1.0"}}}}
```
```json
{"runtimeOptions": {"tfm": "net8.0", "rollForward": "LatestMajor",
  "framework": {"name": "Microsoft.NETCore.App", "version": "8.0.0.0"},
  "configProperties": {"System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization": true}}}
```

**Flow:** host resolves tfm/policy from runtimeconfig → walks deps.json targets → picks per-entry: rid-`any` relocated managed assembly (`NetCore/…`) OR best-matching `runtimes/<rid>/native` binary → true package versions survive only inside `assemblyVersion`/`fileVersion` fields.
**Invariant:** resolution NEVER depends on directory scans or version-at-rest: the `/1` slot normalization means the manifest is authoritative even though real versions (10.1.1.0…) differ from slot keys; `rollForward: LatestMajor` deliberately accepts newer major runtimes; BinaryFormatter serialization is explicitly re-enabled by flag because the snapshot tooling deserializes legacy payloads.
**Probe:** deterministic: `grep -c '"rid"' JetBrains.dotTrace.Viewer.deps.json` → 129; 99 target slots all end `/1`; exactly 16 runtimeTargets paths live outside `NetCore/` — all under `runtimes/<rid>/native/` (verified by parse).
**Coverage caveat:** JSON planes are not symbol-indexed; evidence is direct read + check_index_coverage best-effort record.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dottrace",
  paths: ["JetBrains.dotTrace.Viewer.deps.json"] });
// → status "no_recorded_issue", freshness "metadata_match" (stored ignored-suffix artifact, hash-recorded)
```

**Twin instance:** `resharperhost-worker-fleet-manifests` (Rider lane) uses the same deps.json/runtimeconfig pair for per-worker dependency-graph ISOLATION inside an IDE; this capsule documents the standalone-tool variant where the manifest must also survive wholesale asset relocation (`NetCore/`) and version-slot normalization.

## Verdict
Adopt the three-part contract: relocated `runtimeTargets` paths + normalized version slots + explicit runtime policy flags — a registry-free dependency graph that survives asset relocation. Adapt the prefix (`NetCore/`) and slot grammar to your layout. Omit the specific third-party corpus.
