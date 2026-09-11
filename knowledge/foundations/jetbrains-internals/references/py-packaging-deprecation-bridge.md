<!-- capsule-v2 -->
# Legacy packaging API deprecation bridge — how does the shipped surface migrate pip/package management without breaking plugins?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the old `PyPackageManager` contract, where did it move, and what must a porter know about the transition?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/packaging/PyPackageManager.java:14` — `@Deprecated(forRemoval = true) abstract class PyPackageManager implements Disposable`; doc points to `com.jetbrains.python.packaging.management.PythonPackageManager`; service access `getInstance(Sdk)` :26 → `PyPackageManagers.getInstance().forSdk(sdk)` (registry `PyPackageManagers.java` also `@Deprecated(forRemoval = true)`); core hooks `install(List<PyRequirement>, List<String> extraArgs)` / `getPackages()` / `refreshAndGetPackages(boolean alwaysRefresh)`; topic `PACKAGE_MANAGER_TOPIC` broadcast `TO_DIRECT_CHILDREN`; extension point `shouldSubscribeToLocalChanges()` default true. Bridge exception `PyExecutionException.kt:12` (`@ApiStatus.Obsolete`, wraps `PyError` into `ExecutionException` — "Migrate to [PyError], please").
**Signature:** per-SDK manager instance, NOT a global service — `forSdk` is the multiplexing point.
**Data Shape:** `PyPackage(name, version, location?, requirements)` with THREE telescoping ctors (:17/:23/:27) and `matches(PyRequirement)` → `requirement.match(List.of(this)) != null`.

### Decisive source
```java
// PyPackageManager.java:12-14
/**
 * @deprecated use {@link com.jetbrains.python.packaging.management.PythonPackageManager}
 */
@Deprecated(forRemoval = true)
public abstract class PyPackageManager implements Disposable {
// PyPackageManagers.java doc: "To get an instance of PythonPackageManager consider using
//  PythonPackageManager.Companion.forSdk(Project, Sdk)"   ← Project becomes a required argument
```

**Flow:** old world = SDK-keyed singleton registry + refresh/poll; new world = project-scoped coroutine manager (`forSdk(Project, Sdk)`), errors as `PyResult` not exceptions.
**Invariant:** the migration moved BOTH the lookup key (adds Project) AND the error channel (exception → PyResult) at once — porting only one half strands callers; `refreshAndGetPackages(alwaysRefresh=false)` semantics (cached vs forced) survive across both APIs.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'Deprecated' com/jetbrains/python/packaging/PyPackageManager.java` → `1`;
`grep -n 'forRemoval' com/jetbrains/python/packaging/PyPackageManagers.java` → 1 hit;
`grep -c 'public PyPackage(' com/jetbrains/python/packaging/PyPackage.java` → `3`;
`grep -n 'Obsolete' com/jetbrains/python/packaging/PyExecutionException.kt` → 1 hit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyPackageManager forSdk getPackages refreshAndGetPackages", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the two-axis (key-scope × error-channel) deprecation framing. Adapt: to your vN→vN+1 API. Omit: management-service UI plumbing.
