<!-- capsule-v2 -->
# rider-dotnet-asset-plane — what does a JVM IDE ship for its non-JVM language runtime?

**Source:** JetBrains installed distributions (proprietary), Rider `262.8665.400` `plugins/` tree decisive instance. **Question:** How does an IntelliJ-platform IDE package its .NET-side counterpart (debugger worker, model DLLs, keymap alternatives) without merging runtimes?

## rider-unity/dotnetDebuggerWorker + DotFiles + per-IDE keymap packs
**Path/Symbol:** `rider/plugins/rider-unity/dotnetDebuggerWorker/JetBrains.ReSharper.Plugins.Unity.Rider.Debugger.dll`(+`.xml` doc comments, +`JetMetadata.sstg`), `JetBrains.Unity.Model.dll`; same pattern in `rider-plugins-fsharp/dotnetDebuggerWorker/`, `rider-godot/dotnetDebuggerWorker/`, plus `plugins/{DotFiles, dotCommon, dotCover, dotTrace.dotMemory, debuggerLinq, debuggerMcp, debugger-streams-plugin}`; keymap alternatives: `plugins/keymap-{resharper,visualAssist,visualStudio,visualStudio2022,vscode}`; localization trio `plugins/localization-{ja,ko,zh}`.
**Signature:** `.sstg` = JetBrains metadata stub bundle consumed by the .NET debugger worker; `.xml` sits beside each `.dll` as .NET XML-doc convention — the only "API documentation" surface these binaries expose.
**Data Shape:** no .jar inside dotnetDebuggerWorker; the JVM plugin jar lives in the sibling `lib/` while the native-side assets ride a parallel directory — two runtimes, one plugin id.

### Decisive source
```
$ ls rider/plugins/rider-unity
com  DotFiles  dotnet  dotnetDebuggerWorker  EditorPlugin  lib
$ ls rider/plugins/rider-unity/dotnetDebuggerWorker | head
JetBrains.Plugins.ReSharperUnity.debugger.debugger-worker.JetMetadata.sstg
JetBrains.Plugins._Unity.Pregenerated.BackendModel.JetMetadata.sstg
JetBrains.ReSharper.Plugins.Unity.Rider.Debugger.dll
JetBrains.ReSharper.Plugins.Unity.Rider.Debugger.xml
JetBrains.Unity.Model.dll
JetBrains.Unity.Model.xml
```

**Flow:** JVM side (lib/*.jar) hosts the RD-protocol backend → on debug session start it launches the platform-appropriate `dotnetDebuggerWorker` from the plugin dir → worker loads `.sstg` metadata to map managed frames → model DLLs (`*.Model.dll`) keep the JVM/.NET protocol contracts versioned TOGETHER inside one plugin directory.
**Invariant:** cross-runtime plugins keep their non-JVM payload OUTSIDE lib/ in named asset dirs (`dotnetDebuggerWorker/`, `DotFiles/`, `EditorPlugin/`) so packaging/signing/classpath never mixes runtimes; the XML doc files are the contract reference for the DLLs — read them before assuming any API.
**Probe:** `ls rider/plugins/rider-unity/dotnetDebuggerWorker | grep -c '\.sstg$'` → 2; `ls rider/plugins | grep -c '^keymap-'` → 5 alternative keymap packs riding as ordinary plugins.
**Retrieve:** search_graph project jetbrains-rider query "unity shader debugger backend" resolves the indexed doc-comment plane of these DLLs (pass-1 probe precedent); file layout facts via ls.

## Verdict
Adopt: polyglot products should ship foreign-runtime payloads as sibling asset directories with self-describing docs (.xml) and prebuilt metadata bundles (.sstg analog), keyed by the same plugin identity. Adapt to your host's secondary runtime. Omit sstg binary format. Caveat: extends pass-1's dotnet-profiler note — dotmemory/dottrace lack even this plane (no plugins/ at all).
