<!-- capsule-v2 -->
# Upload retry ladder — how do you retry a failed upload without retrying a cancelled one?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** What does the fail→retry loop look like so stop requests break it and errors accumulate instead of overwrite?

## Bounded retry with inter-attempt sleep, gated on StopRequested
**Path/Symbol:** `ShareX/WorkerTask.cs:DoUploadJob` (:405-419) + `DoUpload` (:428-482).
**Signature:** `private bool DoUpload(Stream data, string fileName, int retry = 0)`
**Data Shape:** returns `isError`; mutates `Info.Result` (reassigned per attempt) and appends to `Info.Result.Errors`; reads `Program.Settings.MaxUploadFailRetry`.

### Decisive source
```csharp
OnUploadStarted();

bool isError = DoUpload(Data, Info.FileName);

if (isError && Program.Settings.MaxUploadFailRetry > 0)
{
    for (int retry = 1; !StopRequested && isError && retry <= Program.Settings.MaxUploadFailRetry; retry++)
    {
        DebugHelper.WriteLine("Upload failed. Retrying upload.");
        isError = DoUpload(Data, Info.FileName, retry);
    }
}

if (!isError)
{
    OnUploadCompleted();
}
```
```csharp
// DoUpload internals
if (retry > 0)
{
    Thread.Sleep(1000);
}
...
catch (Exception e)
{
    if (!StopRequested)
    {
        DebugHelper.WriteException(e);
        isError = true;
        AddErrorMessage(e.ToString());
    }
}
finally
{
    if (Info.Result == null) { Info.Result = new UploadResult(); }
    if (uploader != null) { AddErrorMessage(uploader.Errors); }
    isError |= Info.Result.IsError;
}
```

**Flow:** first attempt → on error, up to `MaxUploadFailRetry` more attempts, each preceded by a fixed 1s sleep → each attempt folds three error sources into the verdict: caught exception (`AddErrorMessage`), uploader's own `Errors` collection, and `Info.Result.IsError` set by the transport itself → success fires `OnUploadCompleted` exactly once.
**Invariant:** a `Stop()` during sleep or between attempts exits the loop without another attempt (`!StopRequested` in the loop condition), and exceptions raised *because of* a stop are not recorded as errors (`if (!StopRequested)` in catch) — cancellation must never be misreported as failure. Errors accumulate across attempts; they are never cleared.
**Probe:** byte-exact probe GREEN pre-write: `isError = DoUpload(Data, Info.FileName, retry);` → 1 match at WorkerTask.cs:412.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "sharex", function_name: "sharex.ShareX.WorkerTask.WorkerTask.DoUpload", direction: "inbound", depth: 1 });
```
Observed: sole caller is `DoUploadJob` — the retry loop owns all re-entry.

## Verdict
Adopt the loop-condition triple (`!stopped && failed && attempts left`) and the cancellation-is-not-failure catch guard. Adapt the fixed 1s backoff to your policy and the error sink to your result type. Omit the large-file warning dialog that precedes this ladder.
