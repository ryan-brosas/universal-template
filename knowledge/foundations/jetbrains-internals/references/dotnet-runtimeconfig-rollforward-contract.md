<!-- capsule-v2 -->
# runtimeconfig rollForward LatestMajor over a private newer runtime — how does a tool pin a floor yet always run newest?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** How do you guarantee 'minimum framework X, newest available wins' across machines you do not control?

## runtimeOptions roll-forward + private runtime satisfaction
**Path/Symbol:** `JetBrains.dotMemory.Standalone.Avalonia.runtimeconfig.json` (14 lines); byte-identical ×3 for the converter fleet (`7c1ecb1a…`); satisfied on Linux by the PRIVATE runtime `linux-x64/dotnet/shared/Microsoft.NETCore.App/10.0.5/` (+ `host/fxr/10.0.5/libhostfxr.so`).
**Signature:** `{runtimeOptions:{tfm,rollForward,framework:{name,version},configProperties:{...}}}`.
**Data Shape:** floor = net8.0/Microsoft.NETCore.App 8.0.0.0; policy = LatestMajor; two config knobs: `Microsoft.NETCore.DotNetHostPolicy.SetAppPaths=true`, `System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization=true`.

### Decisive source
```json
{ "runtimeOptions": {
    "tfm": "net8.0",
    "rollForward": "LatestMajor",
    "framework": { "name": "Microsoft.NETCore.App", "version": "8.0.0.0" },
    "configProperties": {
      "Microsoft.NETCore.DotNetHostPolicy.SetAppPaths": true,
      "System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization": true } } }
```

**Flow:** apphost asks policy for ≥8.0.0 -> LatestMajor prefers the HIGHEST installed/bundled major -> on Linux the launcher-controlled `DOTNET_ROOT` points at the bundled 10.0.5, so the app executes on .NET 10 while declaring 8.
**Invariant:** the declared version is a FLOOR, never the expected runtime; BinaryFormatter re-enablement means legacy deserialization (snapshot readers) must keep working across major jumps — any port that pins an exact runtime or drops the opt-in flag breaks old-snapshot loading.
**Probe:** `md5sum JetBrains.dotMemory.Core.MemoryDumpConverter{,.x86,Test}.runtimeconfig.json` → all `7c1ecb1a844930cd52fe8f1bc50af5f3`; `ls linux-x64/dotnet/shared/Microsoft.NETCore.App/` → `10.0.5` (both executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "snapshot converter hostfxr rollforward", limit: 5 });
```
Caveat: manifest plane; decisive evidence is the direct JSON read above.

## Verdict
Adopt floor+LatestMajor+private-newer-runtime as the shipping posture for long-lived desktop tools; adapt knob names to your framework; omit BinaryFormatter enablement unless you inherit serialized formats that need it.
