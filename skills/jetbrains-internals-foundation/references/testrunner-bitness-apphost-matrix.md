<!-- capsule-v2 -->
# TestRunner bitness/apphost matrix — how does one profiler host unit-test sessions across TFMs, bitnesses, and test frameworks?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** How must a profiling/test-host tool be packaged to attach to arbitrary user test processes regardless of framework generation, bitness, or CPU?

## Per-TFM × per-arch apphost lattice
**Path/Symbol:** `TestRunner/{net35,net472,netcoreapp2.0,netcoreapp3.0}/` × `ReSharperTestRunner{32,64,Arm32,Arm64}` + `DataCollector{32,64}`; adapters at `TestRunner/Adapters/{MsTest,NUnit2,NUnit3,UWP,VsTest,XUnit,XUnit3,XUnit3_2}`.
**Signature:** CoreCLR TFMs ship per-arch quadruples: `ReSharperTestRunner<Arch>{.exe,.dll,.deps.json,.runtimeconfig.json}` PLUS one arch-neutral `ReSharperTestRunner.runtimeconfig.json` (netcoreapp3.0 shows 4 arch variants + 1 neutral = 5 configs); net472 ships exes + `.exe.config` instead.
**Data Shape:** runner core = `JetBrains.ReSharper.TestRunner.{Core,Merged,Utilities,Abstractions}.dll` + `JetBrains.RdFramework.Reflection.dll` (protocol-typed IDE channel) + Serilog console/file sinks; Autofac composition.

### Decisive source
```text
TestRunner/netcoreapp3.0/ $ ls
ReSharperTestRunner32.{exe,dll,deps.json,runtimeconfig.json}
ReSharperTestRunner64.{exe,dll,deps.json,runtimeconfig.json}
ReSharperTestRunnerArm32.… ReSharperTestRunnerArm64.……
Adapters/: MsTest NUnit2 NUnit3 UWP VsTest XUnit XUnit3 XUnit3_2
```

**Flow:** IDE picks TFM dir from the target project → picks arch/bitness variant → launches that prebuilt apphost executable → apphost loads the merged runner core → framework adapter subdir supplies the test-framework bridge → results flow back over the RdFramework reflection protocol.
**Invariant:** bitness/arch is chosen by LAUNCHING DISTINCT PREBUILT APPHOSTS, never by runtime switches — a 32-bit target needs a 32-bit process you cannot retrofit; each CoreCLR arch gets a full quadruple because deps/runtimeconfig belong to the apphost pair; framework differences are quarantined in adapter payloads, never in the runner core.
**Probe:** deterministic counts: `ls TestRunner/Adapters | wc -l` → 8; `ls TestRunner/netcoreapp3.0 | grep -c runtimeconfig.json` → 5 (32/64/Arm32/Arm64 + one arch-neutral); TFM payload dirs = 4 (`net35`,`net472`,`netcoreapp2.0`,`netcoreapp3.0`) beside `Adapters/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "test runner adapters", limit: 5 });
// → TestRunner/Adapters/XUnit/netstandard2.0/xunit.runner.utility.netcoreapp10.xml doc nodes
//   (verified live). The runner core ships no XML docs; its shape is proven by the layout census.
```

**Twin instance:** `resharperhost-worker-fleet-manifests` (Rider lane) cites the in-IDE TestRunner/netcoreapp2.0 deps.json of the same runner family; this capsule documents the full standalone lattice (4 TFM dirs × 4 arch apphosts × 8 framework adapters) shipped with the profiler.

## Verdict
Adopt the lattice: TFM directories × prebuilt per-arch apphosts × pluggable framework adapters × protocol-typed IDE channel. Adapt the adapter list and protocol. Omit the proprietary runner internals.
