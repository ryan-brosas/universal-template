<!-- capsule-v2 -->
# Trigger-manager composition — how do four trigger kinds share ONE launch funnel without duplicating guards?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How are the schedule/watch/event/webhook managers wired to the store, the run tracker, and tryLaunch?

## Shared option contract + per-kind statefulness + one `due`→tryLaunch funnel
**Path/Symbol:** `packages/server/src/index.ts` (:2254–2297 manager construction, :3450–3461 due funnel, :2208–2225 session hooks + notifyRunFinished, :1835–1918 mutation syncs).
**Signature:** Every manager takes `{ debounceMs, postRunGraceMs?, isRunInFlight, getAutomation }`; `isRunInFlight = (id) => { const s = automationStore.get(id)?.runs[0]?.status; return s==="launched" || s==="running"; }`.
**Data Shape:** Debounce/grace constants: watch 500ms / event 500ms / webhook 500ms debounce; grace 1_000ms shared by watch+event (`AUTOMATION_WATCH_POST_RUN_GRACE_MS`, constants.ts:709–728). Statefulness: scheduler = cron map, watch = fs.watch entries, event = listener entries (+ AutomationGitWatcher feeding it), webhook = timers only.

### Decisive source
```ts
automationScheduler.on("due", (automation) => {
    tryLaunch(automation, "schedule");
  });
  folderWatchManager.on("due", (automation) => {
    tryLaunch(automation, "watch");
  });
  sessionEventManager.on("due", (automation) => {
    tryLaunch(automation, "event");
  });
  webhookTriggerManager.on("due", (automation) => {
    tryLaunch(automation, "webhook");
  });
```

**Flow:** every store mutation route (create :1835 / patch :1867 / delete :1895 / reset :1917) calls syncFolderWatchers + syncSessionEventListeners after broadcastAutomations → boot arms both (:3481) → session hooks feed onSessionEvent and BOTH notifyRunFinished calls ride onAutomationExit (:2223–2224) AND the launch-completion path (:2697–2698) → each manager's single `due` emission maps to tryLaunch with its trigger kind.
**Invariant:** The overlap guard (`isRunInFlight`) reads runs[0].status — the LATEST run — so all four trigger kinds share ONE definition of in-flight from the same source of truth. Webhook has NO sync(): nothing to arm. The daemon-global git watcher exists because the per-session GitDiffWatcher only fires when a localterm PTY is live in that repo — event automations must also fire for external git activity. Grace/notify wiring is duplicated deliberately at BOTH exit paths so tab-claimed and headless agent runs both rearm suppression.
**Probe:** `packages/server/src/index.ts:2254–2297` construction block; executed greps from `packages/server/`: `grep -c 'isRunInFlight' packages/server/src/index.ts` → 5 (four manager options + the shared comment line), `grep -cF 'syncFolderWatchers();' packages/server/src/index.ts` → 7 call sites (create :1835 / patch :1867 / delete :1895 / reset :1917 / launch-completion :2658 / PATCH-lowering path :2740 / boot :3481).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "folderWatchManager sessionEventManager webhookTriggerManager tryLaunch", limit: 10 });
```

## Verdict
Adopt the shared-option-contract + single-funnel composition; adapt which kinds you support. Wiring-level evidence via executed greps + graph retrieval; behavior pinned by the three manager suites.
