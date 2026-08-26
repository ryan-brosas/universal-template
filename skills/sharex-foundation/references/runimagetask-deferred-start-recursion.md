<!-- capsule-v2 -->
# RunImageTask deferred start — how do you insert optional interactive gates (quick-task menu, rename dialog) before a task actually queues?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How can task creation wait for user choices without blocking the caller, and how do the gates avoid re-showing forever?

## Menu/window callbacks mutate settings then recurse with skip flags; local closure owns creation
**Path/Symbol:** `ShareX/UploadManager.cs:UploadManager.RunImageTask` (:350-406) + destination-forcing callers `UploadImage` (:408-447).
**Signature:** `public static void RunImageTask(TaskMetadata metadata, TaskSettings taskSettings, bool skipQuickTaskMenu = false, bool skipAfterCaptureWindow = false)`
**Data Shape:** in: TaskMetadata wrapping a Bitmap + mutable TaskSettings; gates invoke callbacks asynchronously; actual product is `WorkerTask.CreateImageUploaderTask(...)` → `TaskManager.Start`.

### Decisive source
```csharp
if (!skipQuickTaskMenu && taskSettings.AfterCaptureJob.HasFlag(AfterCaptureTasks.ShowQuickTaskMenu))
{
    QuickTaskMenu quickTaskMenu = new QuickTaskMenu();

    quickTaskMenu.TaskInfoSelected += taskInfo =>
    {
        if (taskInfo == null)
        {
            RunImageTask(metadata, taskSettings, true);
        }
        else if (taskInfo.IsValid)
        {
            taskSettings.AfterCaptureJob = taskInfo.AfterCaptureTasks;
            taskSettings.AfterUploadJob = taskInfo.AfterUploadTasks;
            RunImageTask(metadata, taskSettings, true);
        }
    };

    quickTaskMenu.ShowMenu();

    return;
}

void StartImageTask(string customFileName)
{
    WorkerTask task = WorkerTask.CreateImageUploaderTask(metadata, taskSettings, customFileName);
    TaskManager.Start(task);
}

if (!skipAfterCaptureWindow)
{
    TaskHelpers.ShowAfterCaptureWindow(taskSettings, result =>
    {
        if (result.Accepted)
        {
            StartImageTask(result.FileName);
        }
    }, metadata);

    return;
}

StartImageTask(null);
```

**Flow:** null image/metadata guard → gate 1: if the AfterCaptureJob requests ShowQuickTaskMenu and not skipped, show the menu and RETURN; the selection callback overrides AfterCaptureJob/AfterUploadJob from the chosen workflow and recurses with `skipQuickTaskMenu: true` → gate 2: after-capture rename window unless skipped; only its Accepted callback calls `StartImageTask(fileName)` → base case: factory + TaskManager.Start.
**Invariant:** each interactive gate ends its method with `return`, so the synchronous caller never blocks and never double-starts; recursion always advances because every re-entry passes at least one more `skip* = true` — dismissal (null taskInfo) also proceeds, it does not abort. The start logic lives in ONE local closure so both gates converge on identical creation. Callers like `UploadImage` may pre-force `taskSettings.AfterCaptureJob = UploadImageToHost` when `IsSafeTaskSettings` to bypass jobs entirely for untrusted/IPC sources.
**Probe:** byte-exact probes GREEN pre-write: `WorkerTask task = WorkerTask.CreateImageUploaderTask(metadata, taskSettings, customFileName);` → UploadManager.cs:387; skip-flag recursions `RunImageTask(metadata, taskSettings, true);` → :370/:376.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "RunImageTask quick task menu after capture window custom file name", limit: 5 });
```
Observed rank 1: `UploadManager.RunImageTask` (:356-406).

## Verdict
Adopt skip-flag-gated recursive re-entry as the pattern for optional pre-upload prompts: non-blocking first call, single creation closure, guaranteed progress on dismissal. Adapt the two gates' UI and add your own gates by extending the skip-parameter set. Omit QuickTaskMenu internals (next-pass target) and WinForms window plumbing.
