<!-- capsule-v2 -->
# WorkerTask factory null contract — what should a task factory return when the payload can't be loaded, and who absorbs that?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How do you keep "queue this job" call sites simple when construction itself can fail?

## Factories are total functions returning null; TaskManager.Start owns the null guard
**Path/Symbol:** `ShareX/WorkerTask.cs` factories (:74-239) + `LoadFileStream` (:1084-1097) + `ShareX/TaskManager.cs:Start` (:53-79).
**Signature:** `public static WorkerTask CreateFileUploaderTask(string filePath, TaskSettings taskSettings)` (and 6 sibling factories)
**Data Shape:** in: payload reference (path/stream/text/URL) + taskSettings; out: fully-formed WorkerTask in InQueue state, or null on load failure; exceptions from stream-open are shown, not thrown.

### Decisive source
```csharp
if (task.Info.TaskSettings.AdvancedSettings.ProcessImagesDuringFileUpload && task.Info.DataType == EDataType.Image)
{
    task.Info.Job = TaskJob.Job;
    task.Image = ImageHelpers.LoadImage(task.Info.FilePath);
}
else
{
    task.Info.Job = TaskJob.FileUpload;

    if (!task.LoadFileStream())
    {
        return null;
    }
}
```
```csharp
private bool LoadFileStream()
{
    try
    {
        Data = new FileStream(Info.FilePath, FileMode.Open, FileAccess.Read, FileShare.Read);
    }
    catch (Exception e)
    {
        e.ShowError();
        return false;
    }

    return true;
}
```
```csharp
// The kernel boundary absorbs null — callers need not check
public static void Start(WorkerTask task)
{
    if (task != null)
    {
        Tasks.Add(task);

        if (task.Status != TaskStatus.History)
        {
            task.StatusChanged += Task_StatusChanged;
            ...
        }

        TaskAdded?.Invoke(task);
        ...

        if (task.Status != TaskStatus.History)
        {
            StartTasks();
        }
    }
}
```

**Flow:** factory builds the WorkerTask shell (Status=InQueue via private ctor), stamps Job + DataType (FindDataType for file/download factories), applies name patterns, then materializes the payload: image files become decoded Bitmaps under ProcessImagesDuringFileUpload, everything else opens a shared-read FileStream. Any open failure → error dialog/log → **null**, not throw. `CreateDownloadTask` similarly returns null when URL-derived filename sanitizes to empty.
**Invariant:** the null contract is kernel-owned: `TaskManager.Start` opens with `if (task != null)`, so inconsistent caller discipline (`DownloadFile` checks at UploadManager.cs:550, `UploadFile` does not at :56-57) is safe by construction. Second invariant in the same method: History pseudo-tasks (`CreateHistoryTask`, Status=History) are added to `Tasks` and announced but get NO event subscription and NO `StartTasks()` pump — display-only membership is decided by status test inside Start.
**Probe:** byte-exact probes GREEN pre-write: `if (task.Info.IsUploadJob && !task.LoadFileStream())` → WorkerTask.cs:205; `if (task != null)` → TaskManager.cs:55 (+ :83/:125/:196 as predicted for Remove/StopAllTasks/Task_TaskCompleted guards).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "create file uploader task load file stream return null data type", limit: 5 });
```
Observed ranks 1-3: `CreateDataUploaderTask` (:95-103), `LoadFileStream` (:1084-1097), `CreateFileUploaderTask` (:105-133).

## Verdict
Adopt total-function factories with null-on-load-failure plus a single kernel-side null guard so queue call sites stay one line; adopt status-tested display-only membership for pseudo-tasks. Adapt error surfacing (`e.ShowError()` is a modal UI concern) to your environment's logging. Omit the concrete EDataType/name-pattern logic if your type triage differs (see finddatatype-extension-triage).
