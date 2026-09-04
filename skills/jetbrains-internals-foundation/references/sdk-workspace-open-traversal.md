<!-- capsule-v2 -->
# dotMemory SDK — how do you open a workspace file and walk its object graph programmatically?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** What contract governs opening `.dmw` workspaces and traversing snapshots from code, and how is the shipped NuGet kept honest?

## OpenWorkspace tri-path + BFS/DFS callbacks + CI drift guard
**Path/Symbol:** `JetBrains.dotMemory.Sdk.xml` (940 lines): `T:JetBrains.dotMemory.Sdk.DotMemory` (:7-11), `M:...OpenWorkspace(String,Configuration)` (:12-35), callbacks `IBfsCallback/IBfsRefCallback/IDfsCallback` (:36-48); drift guard in `JetBrains.dotMemory.Sdk.Installer.xml`:7-14; scripting surface in `JetBrains.dotMemory.Sdk.Sample.xml`:7-28.
**Signature:** `DotMemory.OpenWorkspace(string path, DotMemory.Configuration cfg)`; traversal callbacks for visiting object graphs and reference graphs separately; `ourExternalPackages` static field on `DotMemorySdkNuGetArtifact`.
**Data Shape:** accepted paths = {`.dmw` file | `workspace.idx` inside the workspace storage folder | `workspace.json` of a manually unpacked dmw}; cache policy switches on which path form was used.

### Decisive source
```xml
<remarks>The <paramref name="path"/> might be: * to dmw-file; * to workspace.idx file inside
dotMemory workspace storage folder; * to workspace.json file of manually unpacked dmw-file;
The dmw-file is unpacked to temp folder ... and then cleaned-up when workspace instance is disposed
(see Configuration.ClearCacheOnClose). Also it is possible to open workspace which is in dotMemory
workspace storage folder. In such case SDK re-uses regular dotMemory cache and doesn't clean-up it
on dispose. ... Opening of CLR/Java dumps currently not implemented</remarks>
<!-- Installer.xml --> WORKAROUND: We need a list of external packages to build SDK nuget package
for unit-testing, but we don't have access to packages info in tests, so we use hard-coded one.
This list is generated on `Installer, Portable, Zip` step ... If differences are detected then
build fails and list must be updated.
```

**Flow:** three path forms -> three cache lifetimes (temp-unpack+cleanup vs storage-folder reuse vs State/Cache created beside manual unpack); graph analysis via BFS/DFS visitor callbacks distinguishing object-walk from reference-walk; SDK ships as NuGet whose external-package closure is pinned by a generated hard-coded list that unit tests compare -> build fails on drift.
**Invariant:** cache ownership is a FUNCTION of the open-path form — a porter who always temp-unpacks destroys incremental re-analysis; the NuGet artifact has NO trusted package metadata source at test time, so parity is enforced by fail-the-build diffing instead.
**Probe:** `grep -c 'Script' JetBrains.dotMemory.Sdk.Sample.xml` ≥ 3 with `/dev` Scripting-view remarks (`dotMemory.UI.64 /dev`; rollout dir `%AppData%\JetBrains\dotMemory\scripting\precompiled`); Roslyn present: `ls NetCore/Microsoft.CodeAnalysis.CSharp.Scripting.dll` (both executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "Sdk OpenWorkspace workspace idx callback", limit: 8 });
```

## Verdict
Adopt tri-path workspace opening with path-derived cache semantics plus BFS/DFS visitor split; adapt the drift-guard pattern (generated fixture list + failing comparison) to any artifact whose tests cannot see real package metadata; omit the /dev scripting persona unless you ship an embeddable REPL surface.
