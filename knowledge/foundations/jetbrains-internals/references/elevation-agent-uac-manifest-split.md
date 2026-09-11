<!-- capsule-v2 -->
# Elevation-agent UAC manifest split — how does a profiler elevate only the tiny piece that needs privilege?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** Where does the admin boundary live in a profiling product that must inject into other processes, and what proves it when all doc planes are empty?

## requireAdministrator PE manifest on a dedicated agent exe; everything else stays asInvoker
**Path/Symbol:** `JetBrains.Profiler.Windows.ElevationAgent.exe` (24,488-byte PE32 i386 managed assembly; embedded app manifest); contrast `windows-x64/dotTrace.exe` + `dotTraceViewer.exe` (PE32+ x86-64 bootstrappers, zero `requestedExecutionLevel`); activation vocabulary in `JetBrains.Profiler.Windows.Impl.xml:7-54` (`ProfilerActivationFlags`, `WindowsHostManager`).
**Signature:** `<requestedExecutionLevel level="requireAdministrator" uiAccess="false" />` — exactly one occurrence, inside the elevation agent's embedded manifest only.
**Data Shape:** privileged surface = one small dedicated exe; unprivileged UI/bootstrappers never request elevation; RemoteAgent ships as a plain managed dll (+dll.config), no exe at all; `JetBrains.Profiler.Windows.{ElevationAgent,RemoteAgent,Remotable.*}.xml` are all EMPTY `<members/>` stubs — the split is proven by PE manifests + layout, not docs.

### Decisive source
```text
ElevationAgent.exe manifest (probed): requestedExecutionLevel level="requireAdministrator"
  uiAccess="false"   [1 occurrence]
windows-x64/dotTrace.exe manifest probe: 0 occurrences of requestedExecutionLevel
  (asInvoker default) — same for dotTraceViewer.exe
JetBrains.Profiler.Windows.ElevationAgent.xml: <members></members>  (empty, whole file)
```
```xml
<!-- JetBrains.Profiler.Windows.Impl.xml — the non-elevated orchestration vocabulary -->
<member name="F:…ProfilerActivationFlags.GrantedRegistryFree">
  Granted that engine supports COR_PROFILER_PATH_32 / COR_PROFILER_PATH_64 /
  CORECLR_PROFILER_PATH_32 / CORECLR_PROFILER_PATH_64. RegSvr32.exe will not be called.
</member>
<member name="F:…ProfilerActivationFlags.CheckWindowsBuiltinUsersAccessRights">
  Verify and fix BUILDIN\Users access rights before launch. Windows only.
</member>
<member name="T:…WindowsHostManager">
  Explicit host manager implementation suitable for shellless environments
</member>
```

**Flow:** profiler host prepares activation env vars pointing COR/CORECLR_PROFILER_PATH at the engine (registry-free ⇒ no RegSvr32, no admin needed for THAT) → anything that genuinely requires privilege (fixing BUILTIN\Users ACLs, metro access rights) is funneled into the requireAdministrator ElevationAgent process → shellless/remote hosts use WindowsHostManager + the dll-only RemoteAgent instead of interactive elevation.
**Invariant:** elevation is per-binary via PE manifest, never per-code-path inside a shared exe; environment-variable activation (GrantedRegistryFree*) exists precisely so the common path avoids the UAC boundary entirely; empty doc planes must not be read as "no contract here".
**Probe:** deterministic binary probes executed this pass: `grep -c requestedExecutionLevel` = 1 (agent) vs 0 (both bootstrappers) with the exact manifest line extracted from the agent; directory census shows `windows-x64/` contains ONLY the two bootstrappers (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "ElevationAgent ProfilerActivationFlags WindowsHostManager activation", limit: 10 });
// → jetbrains-dottrace.JetBrains.Profiler.Windows.ElevationAgent.doc @ …ElevationAgent.xml
//   (empty-members stub confirmed by graph lines 2-8) — verified live.
```

## Verdict
Adopt the decomposition: isolate every privileged operation behind a minimal manifest-elevated helper binary and keep the main product asInvoker; prefer env-var/registry-free engine activation to shrink what ever needs elevating. Adapt agent size/protocol to your platform. Omit Windows-specific flags elsewhere; document honestly when your own doc generation ships empty planes so future miners don't re-derive the layout evidence.
