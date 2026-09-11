<!-- capsule-v2 -->
# SDK-path classification and startup-safe SDK lookup — how are remote/custom interpreter paths recognized, and why does the sync SDK getter lie during startup?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What does `CustomSdkHomePattern` match, and what is the documented `findPythonSdk` vs `findPythonSdkWaitingForProjectModel` contract?

## Connected graph-selected seam
**Path/Symbol:** `sdk/CustomSdkHomePattern.kt:16` — `CUSTOM_PYTHON_SDK_HOME_PATH_PATTERN = Pattern.compile("^([-a-zA-Z_0-9]{2,}:|\\\\\\\\|//wsl).+")` with doc explaining: scheme prefix needed for `docker-compose:` (hence the hyphen in the char class), WSL forms `\\wsl.local\` / `\\wsl$`, PLUS `//wsl` because "with a new workspace model paths changed on save". `module/PyModuleService.kt`: `suspend fun findPythonSdkWaitingForProjectModel(module)` :20 — "suspends until the project model is fully loaded… safe to call during startup"; plain `findPythonSdk(module)` :30 — "**Startup caveat:** may return null when a Python SDK *is* configured but hasn't resolved yet (stale workspace-model cache)".
**Signature:** regex `matches()` full-string predicate; service located via `project.service<PyModuleService>()`.
**Data Shape:** predicate input = SDK home path string; lookup output = nullable Sdk.

### Decisive source
```
// CustomSdkHomePattern.kt:11-15 doc verbatim:
//   "Note that *\w+.** pattern is not sufficient because we need also the
//    hyphen sign (*-*) for *docker-compose:* scheme."
// PyModuleService.kt:23-26 doc verbatim:
//   "**Startup caveat:** may return `null` when a Python SDK *is* configured but hasn't
//    resolved yet (e.g., the SDK table is still loading from a stale workspace model cache).
//    Prefer [findPythonSdkWaitingForProjectModel] in coroutine contexts."
```

**Flow:** path → regex classify custom-vs-local (scheme/WSL forms) → interpreter handling branches; module → SDK lookup chooses sync (UI, may miss) vs suspending (startup/background, authoritative).
**Invariant:** a NULL from the sync getter means "not yet", never "no" — treating it as absence during startup silently drops interpreters; the regex must accept THREE remote spellings (scheme:, UNC, //wsl) or saved projects re-detect as local.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src/com/jetbrains/python` root:
`sed -n '20p' module/PyModuleService.kt` → suspend signature line;
`grep -c 'Startup caveat' module/PyModuleService.kt` → `1`;
`grep -n 'docker-compose' sdk/CustomSdkHomePattern.kt` → 1 hit;
`sed -n '16p' sdk/CustomSdkHomePattern.kt` → pattern line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "findPythonSdk PyModuleService CustomSdkHomePattern", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: null-means-not-yet-yet semantics + multi-spelling custom-path predicate. Adapt: regex to your remote targets. Omit: Eel/workspace internals.
