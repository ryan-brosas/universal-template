<!-- capsule-v2 -->
# ThreadDoWork finally-cleanup contract — which cleanup steps must survive stop and failure?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** When a job is stopped or throws mid-upload, what cleanup must still run, in what order, and what must be decided *before* disposal?

## KeepImage latch → Dispose → clipboard rollback → deferred file delete, all inside finally
**Path/Symbol:** `ShareX/WorkerTask.cs:ThreadDoWork` (:306-357); early-copy producer at `UploadData` (:899-906).
**Signature:** `private void ThreadDoWork()`
**Data Shape:** inputs: `Image`, `Data`, `EarlyURLCopied`, `Info.Result`; no output — terminal event fires later via `ThreadCompleted`.

### Decisive source
```csharp
finally
{
    KeepImage = Image != null && Info.TaskSettings.GeneralSettings.ShowToastNotificationAfterTaskCompleted;

    Dispose();

    if (EarlyURLCopied && (StopRequested || Info.Result == null || string.IsNullOrEmpty(Info.Result.URL)) && ClipboardHelpers.ContainsText())
    {
        ClipboardHelpers.Clear();
    }

    if ((Info.Job == TaskJob.Job || (Info.Job == TaskJob.FileUpload && Info.TaskSettings.AdvancedSettings.UseAfterCaptureTasksDuringFileUpload))
        && Info.TaskSettings.AfterCaptureJob.HasFlag(AfterCaptureTasks.DeleteFile) && !string.IsNullOrEmpty(Info.FilePath) && File.Exists(Info.FilePath))
    {
        File.Delete(Info.FilePath);
    }
}

if (!StopRequested && Info.Result != null && Info.Result.IsURLExpected && !Info.Result.IsError)
{
    if (string.IsNullOrEmpty(Info.Result.URL))
    {
        AddErrorMessage(Strings.UploadTask_ThreadDoWork_URL_is_empty_);
    }
    else
    {
        DoAfterUploadJobs();
    }
}
```

**Flow:** try block = `DoThreadJob()` (capture post-processing) → `OnImageReady()` → `DoUploadJob()` if upload allowed. The **finally** runs on every exit path: (1) `KeepImage` is latched *before* `Dispose()` because `Dispose()` skips image disposal only when `KeepImage` is true; (2) if an early-copied URL ended up orphaned (stop/empty result), clear the clipboard so a stale link doesn't masquerade as fresh; (3) the user's DeleteFile after-capture job still executes — a stopped or failed upload still deletes the temp capture it was configured to clean up. After-upload jobs run *outside* the finally, gated on `IsURLExpected && !IsError`.
**Invariant:** cleanup ordering is: latch → dispose → rollback → delete; nothing after `Dispose()` may touch `Data`/`Image`. Early-copy rollback triggers only when no durable URL survived (`StopRequested || Result == null || empty URL`) AND the clipboard still holds text.
**Probe:** byte-exact probe GREEN pre-write: `if (EarlyURLCopied && (StopRequested || Info.Result == null || string.IsNullOrEmpty(Info.Result.URL)) && ClipboardHelpers.ContainsText())` → 1 match at WorkerTask.cs:334; producer probe `uploader.EarlyURLCopyRequested += url =>` → 1 match at :901.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "sharex", qualified_name: "sharex.ShareX.WorkerTask.WorkerTask.ThreadDoWork" });
```
Observed: full method body :306-357 matches this capsule byte-for-byte.

## Verdict
Adopt the finally-block ownership of cleanup and the decide-before-dispose latch. Adapt the specific rollbacks (clipboard → whatever side channels your jobs write early). Omit DeleteFile semantics tied to AfterCapture flags — keep the principle "user-requested destructive cleanup still runs on failure."
