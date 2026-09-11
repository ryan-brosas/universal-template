<!-- capsule-v2 -->
# Disposable lifecycle and PSI-icon idioms — how do published Python API classes bind plugin lifetimes and load icons?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is `PythonPluginDisposable` for, what does its dual service level mean, and how are PSI-layer icons declared?

## Connected graph-selected seam
**Path/Symbol:** `com/jetbrains/python/PythonPluginDisposable.java` — `@Service({Service.Level.APP, Service.Level.PROJECT})` :13 (BOTH levels), empty-body `dispose()` :21; accessors app-level `getInstance()` :15 and project-level `getInstance(project)` :18. Icon idiom `psi/icons/PythonPsiApiIcons.java`: private `load(path, cacheKey, flags)` via `IconManager.getInstance().loadRasterizedIcon(path, classLoader, cacheKey, flags)`; constants like `IPythonNotebook = load("icons/com/jetbrains/python/psi/iPythonNotebook.svg", 610765917, 0)` with nested `Nodes` class for element icons (`CyanDot`, negative-int cache key). Scope plumbing: `codeInsight/controlflow/ScopeOwner.java:27` — `interface ScopeOwner extends AstScopeOwner, PyElement` (empty marker bridging AST layer to Python layer).
**Signature:** disposable obtained per scope; subscriptions `messageBus.connect(PythonPluginDisposable.getInstance(project))` pattern.
**Data Shape:** one class, two service instances (app + one per project) chosen by which getter you call.

### Decisive source
```java
// PythonPluginDisposable.java:12-21
@Service({Service.Level.APP, Service.Level.PROJECT})
public final class PythonPluginDisposable implements Disposable {
  public static @NotNull Disposable getInstance() { … }              // application level
  public static @NotNull Disposable getInstance(@NotNull Project project) { … }  // project level
  @Override public void dispose() { }   // empty body: lifetime CONTAINER, not a resource
```

**Flow:** plugin code connects listeners/alarms to this disposable → IDE disposes it when the app or project closes → subscriptions die with the right scope. Empty dispose() is CORRECT — the class exists to be a parent lifetime token.
**Invariant:** choosing the wrong getter leaks or kills early (app-level subscription in a project component outlives the project); icons are loaded through IconManager with a STABLE hand-picked cache key (hash-like int, may be negative) so recoloring/theming can evict correctly.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src/com/jetbrains/python` root:
`grep -n 'Service({Service.Level.APP, Service.Level.PROJECT})' PythonPluginDisposable.java` → :13;
`grep -c 'public static @NotNull Disposable getInstance' PythonPluginDisposable.java` → `2`;
`grep -n 'loadRasterizedIcon' psi/icons/PythonPsiApiIcons.java` → 1 hit;
`sed -n '27p' codeInsight/controlflow/ScopeOwner.java` → marker interface line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PythonPluginDisposable getInstance Disposable", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: shared disposable-per-scope as THE plugin lifetime idiom; icon-manager constant table. Adapt: service locator to your DI. Omit: rasterized-icon caching internals.
