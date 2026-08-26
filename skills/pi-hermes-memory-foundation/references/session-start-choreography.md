<!-- capsule-v2 -->
# Session-start choreography — in what order must a session_start handler initialize persistence, rebind project scope, and schedule backfill so a failed migration degrades instead of wedging the extension?

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** What is the exact ordered startup ladder inside `session_start`, and which steps are allowed to fail silently?

## The §1 handler is an ordered ladder with one latch and one gate
**Path/Symbol:** `src/index.ts` session_start handler (:166–218); `persistenceInitialized` latch (:106); open-guard install (:119–128, mechanics owned by lazy-native-binding.md).
**Signature:** `pi.on("session_start", async (_event, ctx: { cwd; sessionManager; ui? }) => void)`.
**Data Shape:** no return value consumed; failures must be swallowed or notified — the host does not surface handler throws at startup.

### Decisive source
```ts
// src/index.ts:168-187, 206 (condensed to the load-bearing skeleton)
if (!persistenceInitialized) {
  try {
    await migrateThenSyncMarkdownMemories(dbManager,
      shouldMigrateExtensionRoot ? legacyGlobalDir : null, globalDir,
      config.projectsMemoryDir, agentRoot,
      { onMigrationSucceeded: () => { databaseMigrationPending = false;
                                     dbManager.setOpenGuard(null); } });
    persistenceInitialized = true;
  } catch {
    // Best-effort only: migration or SQLite backfill must not block startup.
  }
}
const nextProject = detectProject(config.projectsMemoryDir, ctx.cwd);
if (nextProject.memoryDir !== projectMemoryDir) {   // rebind ONLY on change
  projectMemoryDir = nextProject.memoryDir ?? null;
  projectStore = createProjectStore(nextProject);
  configureProjectStore(projectStore);            // consolidator injection
  configureMemoryToolProjectStore(projectStore);  // memory tool target swap
}
…
refreshSkillProjectContext(ctx.cwd);
await skillStore.migrateLegacySkills();
await skillStore.ensureDiscoveredRoots();
await store.loadFromDisk();
if (projectStore) await projectStore.loadFromDisk();
if (standingStore) await standingStore.load();
if (persistenceInitialized) scheduleSessionBackfill(dbManager, sessionsDir, …);
```

**Flow:** (1) FIRST session start runs the legacy→extension-root Markdown merge + SQLite sync once, behind the `persistenceInitialized` latch so repeat events are no-ops and any throw degrades to "no SQLite mirror this session" instead of blocking startup; success clears the DB open-guard. (2) Project scope rebinding keys on a DIFFED `memoryDir`, not raw cwd — an unchanged dir never reconstructs stores. (3) Skill context refresh → legacy skill migration → discovered-roots mkdir → global/project/standing loads, in that order, so migrations precede reads. (4) Backfill scheduling is GATED on the latch: if initialization failed, past-session import silently does not run rather than racing an unsynced mirror.
**Invariant:** startup must never throw out of `session_start`; the only state that survives a failed init is "SQLite features off" — Markdown authority still loads. Rebind fires exclusively on memoryDir change; both indirection callbacks (`configureProjectStore`, `configureMemoryToolProjectStore`) must receive the new store together so tools and consolidation never disagree about the active project.
**Probe:** `tests/project-rebinding.test.ts` — launches the whole default export from a temp launch dir with `PI_CODING_AGENT_DIR` set pre-import, then drives `session_start({cwd: targetDir})` + `before_agent_start`: the composed system prompt contains TARGET-dir memory and NOT launch-dir memory. Executed GREEN pre-write: 1 passed / 0 failed. Coverage: `src/index.ts` + test path `no_recorded_issue` @ gen 2026-08-24T14:05:19Z.
**Cross-references:** backfill scheduler internals → deferred-task-singleton.md; migrate/sync interiors → authoritative-file-scanner-hardening.md; open-guard semantics → lazy-native-binding.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "session_start persistenceInitialized migrateThenSyncMarkdownMemories scheduleSessionBackfill detectProject", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the ladder shape: one-shot best-effort init latch → diff-gated project rebind through paired indirection callbacks → migrate-before-load ordering → feature gating on init success. Adapt step boundaries to your host's session lifecycle hooks. Omit the legacy-dir migration branch when you have no historical layout. Caveat: the end-to-end probe covers the happy rebind path only; the latch-failure degradation is source-pinned (:184–186 comment) without a dedicated upstream test.
