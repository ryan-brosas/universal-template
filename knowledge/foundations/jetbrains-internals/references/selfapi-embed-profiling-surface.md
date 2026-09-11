<!-- capsule-v2 -->
# SelfApi self-profiling lifecycle — how does an app profile itself (or a neighbor) in production?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** What is the minimal API to trigger memory snapshots from inside a deployed application?

## JetBrains.Profiler.SelfApi.DotMemory lifecycle
**Path/Symbol:** `JetBrains.Profiler.SelfApi.xml` (653 lines): `T:JetBrains.Profiler.SelfApi.DotMemory` (:47-65), config fluent set `T:CommonConfigHelpers` (:12-46). Graph anchor: `jetbrains-dotmemory.JetBrains.Profiler.SelfApi.doc` lines 2-653.
**Signature:** lifecycle census (grep-verified): `Init / InitAsync / InitOffline / Config / Attach / Detach / GetSnapshot / GetSnapshotOnce / EnsurePrerequisite(Async)`; config helpers `ProfileExternalProcess<T>(int pid)`, `DoNotUseApi<T>()`, `UseLogFile<T>(string)`, `WithCommandLineArgument<T>(string)`, `UseCustomResponseTimeout<T>(int)`.
**Data Shape:** default = same-process profiling; external-pid opt-in; session control via `JetBrains.Profiler.Api` OR fallback to command-line profiler SERVICE MESSAGES; command-line profiler tool auto-downloaded.

### Decisive source
```xml
<member name="M:...CommonConfigHelpers.ProfileExternalProcess``1(``0,System.Int32)">
  <summary>By default self-api profiles the same process it was run in.
  With this option it is possible to profile another process by its pid</summary>
<member name="T:JetBrains.Profiler.SelfApi.DotMemory">
  <summary>The API lets you initiate and control profiling sessions right from the code
  of your application ... The API uses the dotMemory command-line profiler
  (the tool is downloaded automatically)</summary>
  <remarks>* to initialize the API, call DotMemory.Init()
  * to get just one memory snapshot, call DotMemory.GetSnapshotOnce
  * or in case you need several snapshots, call Attach/GetSnapshot*/Detach</remarks>
```

**Flow:** Init (or InitAsync/InitOffline for no-network contexts; EnsurePrerequisite pre-checks downloads) -> Config fluently tunes (pid target, log file, response timeout, raw args) -> Attach -> N×GetSnapshot -> Detach; single-shot shortcut GetSnapshotOnce.
**Invariant:** snapshotting must degrade gracefully when the CLI profiler is absent/slow: UseCustomResponseTimeout closes the session on attach/detach non-response, and DoNotUseApi proves session control has TWO channels (in-proc API vs service messages) — a port hardwired to one channel breaks offline/ad-hoc modes.
**Probe:** `grep -oE 'M:JetBrains\.Profiler\.SelfApi\.DotMemory\.[A-Za-z]+' JetBrains.Profiler.SelfApi.xml | sort -u` → exactly the nine lifecycle names above (executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "SelfApi DotMemory Init snapshot attach", limit: 8 });
```

## Verdict
Adopt the Init→Config→Attach→GetSnapshot*→Detach lifecycle with pid-targeting and dual-channel session control; adapt the auto-download prerequisite ladder to your distribution; omit the service-message channel only if you never profile air-gapped hosts.
