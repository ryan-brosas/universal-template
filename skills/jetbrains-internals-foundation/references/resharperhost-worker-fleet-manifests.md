<!-- capsule-v2 -->
# ReSharperHost worker-fleet manifests — how do you ship many cooperating .NET processes inside one IDE install without merging their dependency graphs?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`lib/ReSharperHost/*.deps.json`, `TestRunner/netcoreapp2.0/*.deps.json`, platform dirs); Codebase Memory `jetbrains-rider`. **Question:** When one host spawns several helper runtimes (backend analysis, debugger, Roslyn, stack sampling, SSH sidecar…), how are their managed dependency graphs versioned and isolated?

## The fleet as the decisive instance
**Path/Symbol:** `lib/ReSharperHost/Rider.Backend.deps.json` (targets `.NETCoreApp,Version=v8.0`, 133 libs) vs `TestRunner/netcoreapp2.0/ReSharperTestRunner64.deps.json` (`.NETCoreApp,Version=v2.0`).
**Signature:** per worker W: `W.deps.json` + `W.runtimeconfig.json` (+ `W.windows.runtimeconfig.json` / `W.netcore.runtimeconfig.json` / `W.ni.netcore.*` variants where OS/runtime flavor differs).
**Data Shape:** fleet census = 12 deps.json: Rider.Backend, JetBrains.Roslyn.Worker, JetBrains.Debugger.Worker, JetBrains.ClrStack.Worker, JetBrains.ProcessEnumerator.Worker, JetBrains.Ijent.Sidecar, JetBrains.Debugger.BrowserHub, JetBrains.BrowserRefresh.Agent.Host, JetBrains.Rider.Backend.EnvironmentAnalyzer, JetBrains.Rider.MacAgent, JetLauncherILc, JetBrains.ReSharper.Features.WinForms.Designer.External.Core. Managed DLLs sit at package root (190 `JetBrains.*.dll` + 192 XML-doc siblings); per-platform APPHOST stems sit inside each platform dir.

### Decisive source
```text
$ ls lib/ReSharperHost/linux-x64/ | head -8
clang-format
dotnet
jb_zip_unarchiver
JetBrains.Debugger.Worker          <- apphost stem (native executable)
JetBrains.ProcessEnumerator.Worker
Rider.Backend
$ python3 -c "import json;d=json.load(open('Rider.Backend.deps.json'));
  k=list(d['targets'])[0];print(k, len(d['targets'][k]))"
.NETCoreApp,Version=v8.0 133
```

**Flow:** host resolves a worker via its manifest pair → apphost stem in the platform dir loads the bundled `dotnet` runtime → deps.json resolves the worker's private closure from package-root DLLs (NuGet stack embedded wholesale: `JetBrains.NuGet.*` ×12 in the backend alone) → runtimeconfig pins TFM/properties per worker, OS-specific overrides as sibling variants.
**Invariant:** TFM is a PER-WORKER decision, not install-wide — the test runner still targets netcoreapp2.0 while the backend targets v8.0 in the same tree; never upgrade one worker's manifest without auditing its consumers. Dependency graphs are isolated by process boundary, not classpath merging. Wrong port: sharing one deps.json across workers — the debugger's closure differs from the backend's NuGet closure deliberately.
**Probe:** `ls lib/ReSharperHost/*.deps.json | wc -l` → 12; `ls lib/ReSharperHost/JetBrains.*.dll | wc -l` → 190; backend target v8.0 vs TestRunner v2.0 grep pair as shown above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-rider", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'lib/ReSharperHost/' AND f.file_path ENDS WITH '.deps.json' RETURN f.file_path LIMIT 20" });
```

## Verdict
Adopt: one self-describing manifest pair per helper process, per-OS config variants as siblings, apphosts localized into platform dirs while managed payloads stay shared. TWIN INSTANCES (dotTrace lane): deps-json-relocated-runtime-targets documents the standalone-tool variant whose manifest must additionally survive wholesale asset relocation + /1 version-slot normalization; testrunner-bitness-apphost-matrix documents this same TestRunner family's full standalone TFM×arch×adapter lattice. Adapt TFM choices per worker lifecycle. Omit binary interiors. Caveats: `JetBrains.Debugger.Worker.xml` is an EMPTY <doc/> stub (8 lines, empty <members/>) — no documented API exists for the debugger worker in this build; coverage signal for cited paths was no_recorded_issue/metadata_match.
