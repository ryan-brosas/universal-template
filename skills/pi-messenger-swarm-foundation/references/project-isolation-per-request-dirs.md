<!-- capsule-v2 -->
# Project isolation & per-request dirs — how does one daemon serve many projects without cross-contamination?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are dirs/config resolved PER REQUEST and what stays global?

## cwd-keyed caches + x-caller-cwd priority + scopeToFolder filter
**Path/Symbol:** `harness/server.ts:getMessengerDirs` (:47-58), `dirsForCwd` (:94-106), `configForCwd` (:111-117), project-cwd priority (:540-555); `config.ts:loadConfig(cwd)`; `store/agents.ts` cwd filter (:132-134, :177-179).
**Signature:** `dirsForCwd(cwd): Dirs` memoizes `Map<cwd, Dirs>` and bootstraps that project's registry/channels on first sight.
**Data Shape:** env ladder for base dir: `PI_MESSENGER_DIR` override > `PI_MESSENGER_GLOBAL=1` legacy home > `<realpathCwd>/.pi/messenger` default.

### Decisive source
```ts
// Priority: x-caller-cwd header > registration file's cwd > PI_MESSENGER_CWD env > server process.cwd()
let projectCwd = callerCwd ? normalizeCwd(callerCwd)
  : normalizeCwd(process.env.PI_MESSENGER_CWD ?? process.cwd());
const preState = resolveAgentState(startupDirs, callerPid, agentName, channelHint, sessionId);
if (preState.state.registered && preState.resolvedCwd) {
  projectCwd = preState.resolvedCwd;   // registration reflects the agent's true project
}
const dirs = dirsForCwd(projectCwd);
```
```ts
if (scopeToFolder) filtered = filtered.filter((a) => a.cwd === myCwd);  // realpath'd compare
```

**Flow:** startup bootstraps ONLY the server's own cwd; each request re-resolves project from header → registration → env → process cwd, then lazily creates that project's `.pi/messenger/{registry,channels}` + defaults. Config cache is cleared wholesale by `/restart`. Agent visibility between projects is cut TWICE: different dirs (state isolation) AND cwd-equality filter on peer listings (scopeToFolder default true).
**Invariant:** normalizeCwd uses `fs.realpathSync.native` BEFORE comparing cwds — macOS `/tmp` symlink aliases would otherwise split one project into two meshes. The legacy global mode is explicitly "not recommended" because it merges ALL projects' registries.
**Probe:** direct tests `tests/swarm/per-request-project.test.ts::different projects get different messenger directories` (:87), `::project B agent can find its channels even when server started from project A` (:199), `tests/swarm/project-isolation.test.ts::should isolate feed events between projects` (title occurs TWICE :136/:372 — first is project-scoped dirs, second cross-project spawn leak), `::should prevent agents from claiming tasks in other projects` (:175); `grep -c "realpathSync.native" store/shared.ts harness/server.ts` (=1 each).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "dirsForCwd configForCwd projectCwd scopeToFolder normalizeCwd", limit: 6 });
```

## Verdict
Adopt per-request dir/config resolution with realpath normalization and the dual isolation (dirs + cwd-filter); adapt the header name; keep the lazy per-project bootstrap or multi-project servers fail on first foreign request.
