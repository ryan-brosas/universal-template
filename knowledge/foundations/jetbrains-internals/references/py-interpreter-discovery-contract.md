<!-- capsule-v2 -->
# Interpreter-discovery env contract — how does the shipped API locate virtualenvs/pyenv interpreters across OSes?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** Which environment variables and default directories does `VirtualEnvReader` consult, and how is the singleton testable?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/venvReader/VirtualEnvReader.kt` — private ctor `(forcedVars: Map<String,String>?, forcedOs: EelOsFamily?)` :14-16 with `@TestOnly` secondary :21-28 (the ONLY injection seam); companion `internal val Instance = VirtualEnvReader(null, null)` :265; defaults `DEFAULT_VIRTUALENVS_DIR = ".virtualenvs"` :274, `PYENV_DEFAULT_DIR_NAME = ".pyenv"` :279; lookups `getVEnvRootDir(eel)` :63 → `resolveDirFromEnvOrElseGetDirInHomePath(eel, "WORKON_HOME", DEFAULT_VIRTUALENVS_DIR)`, `getPyenvRootDir` :75 (`PYENV_ROOT`), enumerators `findVEnvInterpreters() :71-72` / `findPyenvInterpreters() :80-81` both funnel into `findVenvsInDir(root) :87`; pyenv-real check compares against canonicalized root :120. All discovery methods annotated `@RequiresBackgroundThread`.
**Signature:** `resolveDirFromEnvOrElseGetDirInHomePath(eel, ENV_VAR, defaultDir)` — env override else home-relative default.
**Data Shape:** returns `List<PythonBinary>`; paths via Eel (OS abstraction), not java.io.File.

### Decisive source
```kotlin
// VirtualEnvReader.kt:62-72
@RequiresBackgroundThread
fun getVEnvRootDir(eel: EelApi? = getLocalEelIfApp()): Directory {
  return resolveDirFromEnvOrElseGetDirInHomePath(eel, "WORKON_HOME", DEFAULT_VIRTUALENVS_DIR)
}
@RequiresBackgroundThread
fun findVEnvInterpreters(): List<PythonBinary> =
  findVenvsInDir(getVEnvRootDir())
// :40 "Use [Instance]. Provide \"forced\" vars to ctor for tests only."
```

**Flow:** enumerate = resolve root (env var wins over home default) → scan dir for env layouts → collect interpreter binaries; pyenv roots nest under `<pyenv>/versions`.
**Invariant:** env-var override is consulted EVERY call (no snapshot at startup) — tools that export WORKON_HOME late still take effect; the forced-vars ctor is the single test hook — porting discovery to read real env in tests makes suites machine-dependent.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'WORKON_HOME\|PYENV_ROOT' com/jetbrains/python/venvReader/VirtualEnvReader.kt` → `2`;
`sed -n '265p;274p;279p' com/jetbrains/python/venvReader/VirtualEnvReader.kt` → the three lines verbatim;
`grep -c '@RequiresBackgroundThread' com/jetbrains/python/venvReader/VirtualEnvReader.kt` → ≥4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "VirtualEnvReader getVEnvRootDir findVEnvInterpreters", limit: 5, fields: ["signature", "name", "file"] });
// getVEnvRootDir :62-65 rank-2 line-exact
```

## Verdict
Adopt: env-else-home resolution + background-thread discipline + injected-env testability. Adapt: Eel to your path layer. Omit: conda/system flavors (separate EPs).
