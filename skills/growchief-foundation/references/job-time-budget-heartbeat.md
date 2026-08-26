<!-- capsule-v2 -->
# Job time budget + heartbeat — how do hard job deadlines, activity heartbeats, and a kill broadcast compose without orphaning the browser?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** what is the outer supervision layer above `runProcess`, and how does an observable (human-watching) run differ?

## Promise.any(heartBeat, process, maximumRunTime) → abort → killEverything$
**Path/Symbol:** `shared/server/bots/bot.manager.ts:run` (:143-222) with `heartBeat` (:109-135); budget constants :31-33.
**Signature:** `run(isActivity = false, params): Promise<ProgressResponse> | Observable<any>`; `heartBeat(isActivity, abortSignal?): Promise<'kill'>`.
**Data Shape:** `screenshots$ = new BehaviorSubject<string|null>(null)` (always-latest for late subscribers), `killEverything$ = new Subject<'kill'>()`, one shared `AbortController`. Budgets: MAXIMUM_RUNNING_TIME 300s (outer), MAXIMUM_PROCESS_TIME 240s (inner watcher), MAXIMUM_NAVIGATION_TIME 60s (`browser.setDefaultTimeout`).

### Decisive source
```ts
const maximumRunTime = this._maximumJobTime(abortController.signal,
  params.deadline || MAXIMUM_RUNNING_TIME, 'kill' as const);
const process = new Promise<ProgressResponse>(async (res) => {
  try { res(await this.runProcess(abortController, {...})); }
  catch (err) { res({ delay: 0, repeatJob: false, endWorkflow: true }); } // never rejects
});
const race = Promise.any([this.heartBeat(isActivity, abortController.signal),
                          process, maximumRunTime]).then(async (p) => {
  abortController.abort();                       // stop all signal-listening timers
  if (p === 'kill') { killEverything$.next('kill'); throw new Error('Retry job after timeout'); }
  return p;
});
if (params.isObservable) {
  return screenshots$.asObservable().pipe(map((p) => ({ event: 'data', data: p })),
    finalize(() => { try { killEverything$.next('kill'); } catch {} })); // client-left ⇒ kill
}
return race;
```

**Flow:** heartBeat loops `heartbeat(); await timer(10000)` ONLY when running inside a Temporal activity (non-activity mode parks forever on an unresolved inner promise, leaving the race to the other two); whichever finishes first wins the `.any`, everything gets aborted, and a 'kill' winner both broadcasts `killEverything$` (subscriber closes the page + unsubscribes all) and REJECTS so the Temporal caller sees "Retry job after timeout".
**Invariant:** `process` can NEVER reject — its executor catches runProcess throws and resolves to `{endWorkflow:true}` so Promise.any's first-settlement semantics are driven by completion, not failure; the observable branch deliberately returns the screenshots STREAM instead of the promise (fire-and-forget UI session) with `finalize` as the user-disconnect kill switch.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'Promise.any' shared/server/bots/bot.manager.ts` → :185; `grep -n "throw new Error('Retry job after timeout')" bot.manager.ts` → :199; heartbeat gate `if (!isActivity)` → :119-121.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "heartBeat killEverything maximumRunTime", limit: 8 });
```

## Verdict
Adopt: three-way outer race (liveness pulse / work / deadline) with abort fan-out + explicit kill broadcast, and the stream-instead-of-promise observable variant. Adapt budgets; keep the never-rejecting work promise. Omit patchright/Temporal heartbeat specifics.
