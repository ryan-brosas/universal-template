<!-- capsule-v2 -->
# Dual-TFM assembly duplication — why does the same DLL name ship twice in one install?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** When one directory holds two builds of AutoMapper/BouncyCastle/etc., which copy loads and under what contract?

## Root twins vs NetCore/ twins
**Path/Symbol:** `/AutoMapper.dll` vs `/NetCore/AutoMapper.dll`; same pattern for BouncyCastle.Cryptography, Google.Protobuf, JetBrains.Lifetimes, JetBrains.Profiler.Api (5/5 md5 DIFFER: e.g. AutoMapper root `a2e2949c…` vs NetCore `c3c126f7…`). deps.json maps packages into `NetCore/…` (`rid:"any"`).
**Signature:** classic helpers load via root probing + `.exe.config` bindingRedirects; CoreCLR hosts load via deps.json runtimeTargets into NetCore/.
**Data Shape:** every exe carries an identical 1,667-byte `.exe.config`: `<cfg:assemblyBinding>` redirects (System.Buffers/Memory/Numerics.Vectors/Runtime.CompilerServices.Unsafe) PLUS JetBrains' custom namespace `urn:schemas-jetbrains-com:asm-config-metadata` annotating each redirect with `<jb:AssemblyFile Version=…/>`. Helpers WITHOUT `*.runtimeconfig.json`/`*.deps.json` (ExternalStorage.exe, ElevationAgent.exe) are the classic-contract population; hosts WITH them (Standalone.Avalonia.exe, MemoryDumpConverter*.exe) are CoreCLR.

### Decisive source
```xml
<cfg:dependentAssembly>
  <cfg:assemblyIdentity name="System.Memory" publicKeyToken="CC7B13FFCD2DDD51" culture="neutral" />
  <cfg:bindingRedirect oldVersion="0.0.0.0-4.0.2.0" newVersion="4.0.2.0" />
  <jb:AssemblyFile Version="4.0.2.0" xmlns:jb="urn:schemas-jetbrains-com:asm-config-metadata" />
</cfg:dependentAssembly>
```

**Flow:** two resolution contexts coexist in ONE tree: classic-CLR processes bind root copies through redirect table + probing; CoreCLR apphosts ignore .exe.config and follow deps.json into NetCore/. Same simple name, different TFMs, zero collision because resolution never mixes contexts.
**Invariant:** duplication is DELIBERATE per-context layout, not build residue — 'deduplicating' either copy breaks the other fleet. The jb:AssemblyFile annotation makes each redirect traceable to the exact shipped file version.
**Probe:** `for f in AutoMapper.dll BouncyCastle.Cryptography.dll Google.Protobuf.dll JetBrains.Lifetimes.dll JetBrains.Profiler.Api.dll; do md5sum $f NetCore/$f; done | paste - -` → five DIFFERS pairs; `ls -la *.exe.config | awk '{print $5}'` → all 1667 (both executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "Lifetimes Profiler Api assembly doc members", limit: 5 });
```
Caveat: binary/layout plane; graph covers only the XML-doc shadow of each assembly.

## Verdict
Adopt per-context TFM duplication with a manifest-declared remap folder when one install must host classic and CoreCLR consumers; adapt the jb:AssemblyFile metadata idea to annotate your own redirects; omit nothing — dropping either copy is the failure mode this capsule exists to prevent.