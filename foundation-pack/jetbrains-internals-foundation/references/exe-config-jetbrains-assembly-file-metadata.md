<!-- capsule-v2 -->
# exe.config vendor-metadata namespace — how do binding redirects carry vendor data without breaking the classic loader?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** How does one install folder serve BOTH .NET Framework-style resolver rules and CoreCLR policy, and smuggle vendor metadata through a standardized config?

## Dual-regime resolver configs
**Path/Symbol:** `JetBrains.dotTrace.Viewer.exe.config` — 6 of the install's 9 `*.exe.config` carry the vendor namespace (both ExternalStorage variants, Home.Shell, Viewer, Profiler.Windows.ElevationAgent, OperatorsResolveCacheGenerator; Impl/RemoteAgent/Timeline.Standalone stay plain).
**Signature:** `<cfg:dependentAssembly><cfg:bindingRedirect …/><jb:AssemblyFile Version="4.0.4.0" xmlns:jb="urn:schemas-jetbrains-com:asm-config-metadata"/>`.
**Data Shape:** standard `urn:schemas-microsoft-com:asm.v1` bindingRedirects pinned to exact facade versions (System.Buffers/Memory/Numerics.Vectors/CompilerServices.Unsafe); each block carries one extra JetBrains-namespaced child stamping the deployed file version.

### Decisive source
```xml
<cfg:dependentAssembly>
  <cfg:assemblyIdentity name="System.Memory" publicKeyToken="CC7B13FFCD2DDD51" culture="neutral" />
  <cfg:bindingRedirect oldVersion="0.0.0.0-4.0.2.0" newVersion="4.0.2.0" />
  <jb:AssemblyFile Version="4.0.2.0" xmlns:jb="urn:schemas-jetbrains-com:asm-config-metadata" />
</cfg:dependentAssembly>
```

**Flow:** Framework-family loaders consume only the asm.v1 elements (unknown-namespace children are ignorable extension content) → the same folder ALSO holds `.runtimeconfig.json` for the net8.0 host, so one layout boots under either regime; the `jb:` stamps let vendor tooling audit which physical file satisfies each redirect without parsing DLLs.
**Invariant:** vendor metadata MUST be namespaced and additive — the classic parser's tolerance for foreign namespaces is the load-bearing assumption; redirects always pin System.* facades to the exact deployed build.
**Probe:** deterministic: `grep -l 'schemas-jetbrains-com:asm-config-metadata' *.exe.config | wc -l` → 6 of 9; XML-parse proof that all 24 namespaced `AssemblyFile` elements have a `dependentAssembly` parent (0 orphans); namespace URI constant across files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dottrace",
  paths: ["JetBrains.dotTrace.Viewer.exe.config"] }); // best-effort stored-artifact record
```

## Verdict
Adopt namespaced-additive metadata inside standards-defined config blocks (works wherever a strict parser tolerates foreign namespaces), and keep dual resolver regimes side-by-side instead of forking the install tree. Adapt namespace URIs and stamped fields. Omit the specific facade set.
