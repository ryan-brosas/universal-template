<!-- capsule-v2 -->
# Profiler env-var activation vocabulary — how do you inject a profiler into an arbitrary process without registry edits, and which variable names are frozen forever?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** Which environment-variable grammar activates an in-process profiler in a target you don't own, how does the profiler clean up after itself, and where does the registry/elevation fallback still exist?

## Public prefix contract + transparent/chain variable sets
**Path/Symbol:** `JetBrains.Profiler.Windows.SysTools.xml` (270L): `Tools.CoreEnvironmentConstants` (:96-211) — prefix fields (:96-111), diagnostics pair (:112-121), transport/host set (:122-151), transparent-integration set (:152-181), chain-integration set (:182-206), `ProfilerCoreNativeProfParams` (:207-211); `Tools.VariableUtil` per-runtime applicability ladder (:212-259); `EnvironmentPropertyType` classification {:Clr, CoreClr, Mono, Profiler, Normal} (:7-31). Activation flags in `JetBrains.Profiler.Windows.Impl.xml` (56L): `ProfilerActivationFlags` (:7-46).
**Signature:** `String PrefixProfilerCore` (field, removal keyset); `Boolean GrantedRegistryFreeArchitecture` / `GrantedRegistryFree` / `DisableEnvironmentActivation` (flags).
**Data Shape:** every injected variable belongs to exactly one of five classified families (`EnvironmentPropertyType`); engine paths are published per-architecture as a 5-slot transparent set {GUID, Path32, Path64, PathArm32, PathArm64} plus a parallel 5-slot CHAIN set for a second profiler.

### Decisive source
```text
PrefixProfilerCore: "DO NOT CHANGE, THIS IS PUBLIC FOR 3-RD CUSTOMERS !!!
  ONLY FOR CORE CONFIGURATION, BECAUSE CORE REMOVE ENVIRONMENTS BY THAT PREFIX !!!"
ProfilerCoreLogMask / ProfilerCoreLogFile (both): "No that variable == no log."
ProfilerCoreHostPipe: "Host connection address for named pipes, Windows only."
ProfilerCoreGuid / Path32 / Path64 / PathArm32 / PathArm64 (all five):
  "DO NOT CHANGE ... Real profiler GUID/path to N-bit library for transparent integration."
Chain{Guid,Path32,Path64,PathArm32,PathArm64}: "Secondary profiler ... for chain integration."
VariableUtil applicability ladder: EnvCorProfilerPath ".NET Framework 4.5+";
  EnvCorProfilerPath32/64 ".NET Framework 4.6+"; EnvCoreClrProfilerPath ".NET Core 1.0+";
  EnvCoreClrProfilerPath32/64 ".NET Core 1.0+ (x64 only) / .NET 5.0+";
  EnvCoreClrProfilerPathArm32/64 ".NET 6.0+"; EnvDiagnosticPorts ".NET 5.0+"
EnvJetBrainsMonoEnvOptions: "duplicates EnvMonoEnvOptions and allows to get profiler
  parameters when original EnvMonoEnvOptions is cleared (example: profile Unity)"
Impl.ProfilerActivationFlags.GrantedRegistryFreeArchitecture: "Granted that engine supports
  COR_PROFILER_PATH / CORECLR_PROFILER_PATH. RegSvr32.exe will not be called."
DisableEnvironmentActivation: "Don't generate activation environment variables,
  because an another activation way is used."
```

**Flow:** host selects engine library per target architecture → writes the transparent-set variables (GUID + per-arch path) plus optional diagnostics/host vars into the target's environment block BEFORE launch (or via attach helper) → the profiler CORE, once loaded, REMOVES every variable carrying its prefix — self-cleaning so spawned child processes never inherit profiling → when two profilers must coexist, the second rides the reserved CHAIN slots instead of fighting over names → logging/diagnostics are pairwise-gated (mask without file, or file without mask = silence) → if the engine cannot be activated by path variables alone (old arch split), the flag ladder falls back to RegSvr32.exe registration, which needs elevation — that privilege boundary is owned by the separate elevation agent (see elevation-agent-uac-manifest-split).
**Invariant:** the variable-name prefix is simultaneously a frozen third-party API AND the removal keyset — renaming it breaks customers and leaks profiling into children; per-variable runtime applicability is DOCUMENTED FACT (.NET Fx 4.5/4.6, Core 1.0 x64-only until .NET 5 unifies, ARM from .NET 6), not something to probe at runtime; activation is fully suppressible (`DisableEnvironmentActivation`) when another channel drives injection.
**Probe:** deterministic content probes executed this pass on `/mnt/hdd/utopia/inspo/dotmemory/JetBrains.Profiler.Windows.SysTools.xml`: `grep -c "PUBLIC FOR 3-RD CUSTOMERS"` = **6** (prefix field + 5 transparent-set members), `grep -c "No that variable == no log"` = **2**, `grep -c "for chain integration"` = **5**, `grep -c "(x64 only) / .NET 5.0+"` = **2** — all verified against the full 270-line read.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "environment variable profiler activation core constants", limit: 12 });
// → JetBrains.Profiler.doc plane hit; targeted follow-up:
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "SysTools connection server descriptor stream", limit: 6 });
// → JetBrains.Profiler.Windows.SysTools.doc @ JetBrains.Profiler.Windows.SysTools.xml :2-270
//   (file-granular index; member text read directly from the cited ranges).
```

## Verdict
Adopt prefix-scoped self-cleaning env contracts (inject under one reserved prefix, remove by prefix on init) with a documented per-runtime applicability table beside each variable name, and reserve a secondary slot family for coexisting profilers instead of name collisions. Adapt the family classification to your platform. Omit the Windows CLR/CORECLR-specific variable spellings unless porting Windows ETW/CLR profiling; cross-reference elevation-agent-uac-manifest-split for what happens when env activation is unavailable.
