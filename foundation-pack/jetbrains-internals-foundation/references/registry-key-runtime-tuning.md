<!-- capsule-v2 -->
# Registry key runtime tuning — declared feature flags with restart semantics

**Source:** JetBrains IDE installed builds `PyCharm 262.9437.214` / `Rider 262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** How are experimental features declared so users can flip them at runtime without hunting for constants?

## registryKey
**Path/Symbol:** `plugins/python-ce/lib/*.jar:META-INF/plugin.xml` (76 `<registryKey>` declarations across modules) + platform EP `com.intellij.registryKey`-consumed extensions.
**Signature:** `<registryKey key="dotted.name" defaultValue="true|false|<value>" [restartRequired="true|false"] description="..."/>`.
**Data Shape:** key = dotted runtime id; defaultValue typed by content; restartRequired documents whether flipping needs an IDE restart; description = in-product documentation surfaced by the registry UI.

### Decisive source
```xml
<registryKey key="python.explicit.namespace.packages" defaultValue="true"
             restartRequired="true"
             description="Require marking namespace packages explicitly, treat regular directories as implicit source roots" />
<registryKey key="python.toolwindows.available.at.startup" defaultValue="false"
             restartRequired="false"
             description="Python tool windows are available at startup" />
```

**Flow:** plugin declares keys alongside the features they gate → registry UI lists them with defaults/descriptions → user overrides persist outside the jar → code reads values at feature decision points.
**Invariant:** declaration travels WITH the gating plugin (not a central flags file), and restartRequired is per-key metadata, not a global assumption — a porter who makes all flags live-flushing breaks correctness where restartRequired=true. Wrong port: undeclared ad-hoc flag lookups (invisible to users).
**Probe:** deterministic: `grep -c '<registryKey' py-plugin.xml` → 76; `grep 'restartRequired="true"' py-plugin.xml | head -1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "incremental reparse ast", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt co-declared feature flags with explicit restart semantics; adapt storage of overrides; omit IntelliJ Registry UI internals. Coverage caveat: direct jar read.
