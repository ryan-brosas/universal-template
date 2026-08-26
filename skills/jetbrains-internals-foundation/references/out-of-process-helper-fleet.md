<!-- capsule-v2 -->
# Out-of-process profiler helper fleet — why does a profiler spawn x86 twins and elevation agents?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** Which work must leave the UI process, and how is that boundary expressed in the install layout?

## Helper exe census + ETW sampling knobs
**Path/Symbol:** root exes = `JetBrains.Common.ExternalStorage.exe` (+`.x86`), `JetBrains.dotMemory.Core.MemoryDumpConverter.exe` (+`.x86`, +`Test`), `JetBrains.Profiler.Windows.ElevationAgent.exe`, `JetBrains.dotMemory.Standalone.Avalonia.exe`; engine managed wrappers `JetBrains.Profiler.Windows.{Impl,Remotable*,RemoteAgent,SysTools}.dll` + `JetBrains.Etw.dll`; Linux natives `libJetBrains.Profiler.Core{,Api,Transparent}.so` under `linux-x64/`.
**Signature:** `JetBrains.Etw.Param.SamplingParam.#ctor(System.UInt32 frequency)` — 'Sampling frequency in KHz. Valid range: [1KHz - 8KHz]'; `TopRootFactorParam.#ctor(System.UInt32 factor)` — 'first_root_count >= 4 * second_root_count'.
**Data Shape:** modern helpers carry own deps+runtimeconfig (converter trio md5-parity); classic helpers are config-only; the two doc-bearing ETW params are the only published capture-tuning surface.

### Decisive source
```text
$ ls *.exe
JetBrains.Common.ExternalStorage.exe        JetBrains.dotMemory.Core.MemoryDumpConverter.x86.exe
JetBrains.Common.ExternalStorage.x86.exe    JetBrains.Profiler.Windows.ElevationAgent.exe
JetBrains.dotMemory.Core.MemoryDumpConverter.exe   JetBrains.dotMemory.Standalone.Avalonia.exe
JetBrains.dotMemory.Core.MemoryDumpConverterTest.exe
$ grep -A1 'SamplingParam.#ctor' JetBrains.Etw.xml
<param name="frequency">Sampling frequency in KHz. Valid range: [1KHz - 8KHz]</param>
```

**Flow:** heavy/untrusted/elevated work runs OUT of the Avalonia UI process: dump conversion in converter processes (32-bit twin for old 32-bit-target dumps — purpose inferred from twin presence, marked as inference), external storage in its own process, Windows kernel-adjacent capture behind an elevation agent; managed Remotable.Agent/CrossDomain/Proxy assemblies name the cross-domain transport ladder.
**Invariant:** the UI process owns neither conversion nor capture; every helper is separately launchable with its own runtime contract. Wrong port: doing dump parsing or ETW control in-proc — crashes and elevation requirements then kill the whole tool.
**Probe:** `md5sum JetBrains.dotMemory.Core.MemoryDumpConverter*.deps.json` → one hash `a192fb74…` ×3; `grep -c members JetBrains.Profiler.Windows.ElevationAgent.xml` → doc present but `<members>` EMPTY (structural-only evidence, recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "ElevationAgent ETW sampling", limit: 5 });
```

## Verdict
Adopt the split fleet: converter(+arch twins)/storage/elevation as separate processes with per-process runtime manifests; adapt twin policy to your legacy-format matrix; omit Windows ETW specifics on non-Windows ports but keep the [1KHz..8KHz]-style validated knob vocabulary.