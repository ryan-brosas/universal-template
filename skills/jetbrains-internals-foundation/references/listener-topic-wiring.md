<!-- capsule-v2 -->
# Listener topic wiring — declarative pub/sub without registrar code

**Source:** JetBrains IDE installed build `PyCharm 262.9437.214` (PythonCore plugin); Codebase Memory `jetbrains-pycharm`. **Question:** How do components subscribe to lifecycle/publisher events purely via manifest?

## projectListeners / applicationListeners
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (`<projectListeners>` and `<applicationListeners>` blocks; platform EP `com.intellij.configFolderChangedListener`-style topic declarations in PlatformExtensionPoints.xml).
**Signature:** `<listener class="FQN" topic="FQN.of.Publisher" [activeInHeadlessMode="false"]/>` inside `<projectListeners>` or `<applicationListeners>`.
**Data Shape:** class = subscriber implementing the topic's listener interface; topic = publisher interface FQN whose events fan out; headless flag excludes the subscription in command-line runs.

### Decisive source
```xml
<projectListeners>
  <listener class="...PyInterpreterNotificationFileOpenedListener"
            topic="com.intellij.openapi.fileEditor.FileEditorManagerListener" />
  <listener class="...PyDapPluginInstallGotItListener" topic="...XDebuggerManagerListener"
            activeInHeadlessMode="false" />
</projectListeners>
<applicationListeners>
  <listener class="...PySdkTransferredRootsListener" topic="...PySdkListener" />
</applicationListeners>
```

**Flow:** container instantiates the subscriber per project/app scope → subscribes it to every broadcast of the topic interface → events dispatch until teardown; no manual add/remove listener code.
**Invariant:** subscription scope matches block scope — project listeners die with the project, application listeners live for the session; a porter who registers a project-scoped handler on the application bus leaks it across projects. Wrong port: imperative registration scattered through feature code.
**Probe:** deterministic: `grep -A2 '<listener ' py-plugin.xml | grep -c 'topic='` shows multiple topics wired in one file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "sdk available listener notifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt topic-keyed declarative subscriptions for plugin/event buses; adapt scope model; omit IntelliJ messaging infrastructure. Coverage caveat: direct jar read.
