<!-- capsule-v2 -->
# STA ThreadWorker context marshaling — how do per-job worker threads report back to the UI thread safely?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** What is the minimum thread harness so every task event (progress, completion) arrives on the dispatcher that owns the shared UI state?

## One STA background thread per task; events posted to the captured SynchronizationContext
**Path/Symbol:** `ShareX.HelpersLib/ThreadWorker.cs` (:31-83); raisers in `ShareX/WorkerTask.cs:OnStatusChanged…OnUploadersConfigWindowRequested` (:1114-1198).
**Signature:** `public void Start(ApartmentState state = ApartmentState.MTA)` / `public void InvokeAsync(Action action)`
**Data Shape:** two events (`DoWork`, `Completed`); captures `SynchronizationContext.Current ?? new SynchronizationContext()` at construction; no result value — completion carries side effects via the task object.

### Decisive source
```csharp
public void Start(ApartmentState state = ApartmentState.MTA)
{
    if (thread == null)
    {
        thread = new Thread(WorkThread);
        thread.IsBackground = true;
        thread.SetApartmentState(state);
        thread.Start();
    }
}

private void WorkThread()
{
    OnDoWork();
    OnCompleted();   // InvokeAsync(Completed) → context.Post(state => action(), null)
}

public void Invoke(Action action)
{
    context.Send(state => action(), null);
}

public void InvokeAsync(Action action)
{
    context.Post(state => action(), null);
}
```
WorkerTask start: `threadWorker.Start(ApartmentState.STA);` (:251) — clipboard/dialog interop needs STA. Every raiser follows one shape, e.g. `OnImageReady` clones the bitmap first on the worker, then posts a closure that disposes it after handlers run (:1122-1141).

**Flow:** UI thread creates WorkerTask → `ThreadWorker` captures the UI `SynchronizationContext` → job runs on its own STA background thread → all `On*` notifications (`StatusChanged`, `ImageReady`, `UploadStarted`, `UploadProgressChanged`, `UploadCompleted`, `TaskCompleted`, config-window request) are `Post`ed to the captured context → TaskManager handlers (list mutation, tray/title progress) execute on the UI thread.
**Invariant:** because *every* cross-thread notification is marshaled, `TaskManager.Tasks` needs no locking — this is the load-bearing pairing with the admission-gate capsule. The worker thread never raises events directly. `IsBackground = true` keeps process exit unblocked.
**Probe:** byte-exact probes GREEN pre-write: `context.Post(state => action(), null);` → 1 match at ThreadWorker.cs:81; `threadWorker.Start(ApartmentState.STA);` → 1 match at WorkerTask.cs:251.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "ThreadWorker InvokeAsync SynchronizationContext Completed", limit: 10, fields: ["signature", "name", "file"] });
```
Observed: `ThreadWorker.InvokeAsync` / `ThreadWorker.WorkThread` plus WorkerTask raisers in one neighborhood.

## Verdict
Adopt: capture-context-at-construction + Post-everything pattern and one disposable thread per unit of work. Adapt STA/apartment semantics to your runtime (or drop them off-Windows); replace `Send`/`Post` with your dispatcher's invoke forms. Omit WinForms-specific apartment defaults.
