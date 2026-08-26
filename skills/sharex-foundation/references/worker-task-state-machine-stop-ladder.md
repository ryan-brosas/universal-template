<!-- capsule-v2 -->
# Worker task state machine & stop ladder — what must Stop() do in each task state, and who decides the terminal status?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How does a cancellable job distinguish "never start" from "abort mid-upload" without leaking terminal events?

## Per-state Stop + terminal-status computation
**Path/Symbol:** `ShareX/Enums.cs:TaskStatus` (:127-137); `ShareX/WorkerTask.cs:Stop` (:273-290); `OnTaskCompleted` (:1167-1190).
**Signature:** `public void Stop()` / `private void OnTaskCompleted()`
**Data Shape:** states `InQueue, Preparing, Working, Stopping, Stopped, Failed, Completed, History`; `StopRequested` is a one-way latch; terminal event carries no payload — handlers read `task.Status` / `Info.Result`.

### Decisive source
```csharp
public void Stop()
{
    StopRequested = true;

    switch (Status)
    {
        case TaskStatus.InQueue:
            OnTaskCompleted();
            break;
        case TaskStatus.Preparing:
        case TaskStatus.Working:
            if (uploader != null) uploader.StopUpload();
            Status = TaskStatus.Stopping;
            Info.Status = Strings.UploadTask_Stop_Stopping;
            OnStatusChanged();
            break;
    }
}
```
```csharp
// OnTaskCompleted :1167-1185 (terminal decision BEFORE raising)
if (StopRequested)
{
    Status = TaskStatus.Stopped;
    ...
}
else if (Info.Result.IsError)
{
    Status = TaskStatus.Failed;
    ...
}
else
{
    Status = TaskStatus.Completed;
    ...
}

TaskCompleted?.Invoke(this);
Dispose();
```

**Flow:** queued task stopped → immediate `OnTaskCompleted` (it never ran a thread; `Start()` also refuses: `if (Status == TaskStatus.InQueue && !StopRequested)`). Working task stopped → cooperative `uploader.StopUpload()` + `Stopping`; the worker body keeps checking `StopRequested` between stages (`ThreadDoWork`, `DoUploadJob` retry loop), and `ThreadDoWork` sets `StopRequested |= !DoThreadJob()` so stage failure and user stop converge on the same latch.
**Invariant:** exactly one terminal transition per task; `Stopped` beats `Failed` beats `Completed` in that priority order; the terminal status is assigned *before* the event fires so handlers never observe a stale status, and `Dispose()` runs *after* handlers (toasts may still read `task.Image` guarded by `KeepImage`).
**Probe:** byte-exact probes GREEN pre-write: `StopRequested = !DoThreadJob();` → 1 match at WorkerTask.cs:312; enum range read directly at Enums.cs:127-137.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "StopRequested OnTaskCompleted Status Stopped Failed", limit: 10, fields: ["signature", "name", "file"] });
```
Observed: `WorkerTask.Stop` / `WorkerTask.OnTaskCompleted` / `TaskManager.Task_TaskCompleted` cluster together.

## Verdict
Adopt the per-state stop ladder (queue-cancel vs cooperative-abort) and terminal-status-before-event ordering. Adapt `uploader.StopUpload()` to your transport's cancellation token. Omit localized status strings and History pseudo-state.
