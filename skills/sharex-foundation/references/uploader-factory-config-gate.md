<!-- capsule-v2 -->
# Uploader factory & config gate — how is a destination resolved, and what happens when its configuration is invalid?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** Where do per-task overrides, config validation, and filter-based destination routing sit relative to the actual upload call?

## Filter override → CheckConfig → CreateUploader; invalid config becomes an error result, never an exception
**Path/Symbol:** `ShareX/WorkerTask.cs:UploadData` (:884-925), `CheckUploadFilters` (:927-947), `GetInvalidConfigResult` (:1011-1023).
**Signature:** `public UploadResult UploadData(IGenericUploaderService service, Stream stream, string fileName)`
**Data Shape:** inputs: service (from `UploaderFactory.*UploaderServices[destination]`), stream/fileName; `taskReferenceHelper` carries per-task overrides (FTP index, custom-uploader index, text format); returns `UploadResult` or null.

### Decisive source
```csharp
public UploadResult UploadData(IGenericUploaderService service, Stream stream, string fileName)
{
    if (!service.CheckConfig(Program.UploadersConfig))
    {
        return GetInvalidConfigResult(service);
    }

    uploader = service.CreateUploader(Program.UploadersConfig, taskReferenceHelper);

    if (uploader != null)
    {
        uploader.Errors.DefaultTitle = string.Format(Strings.WorkerTask_ErrorTitle, service.ServiceName);
        uploader.BufferSize = (int)Math.Pow(2, Program.Settings.BufferSizePower) * 1024;
        uploader.ProgressChanged += uploader_ProgressChanged;

        if (... EarlyCopyURL)
        {
            uploader.EarlyURLCopyRequested += url =>
            {
                ClipboardHelpers.CopyText(url);
                EarlyURLCopied = true;
            };
        }
        ...
        Info.UploadDuration = Stopwatch.StartNew();
        UploadResult result = uploader.Upload(stream, fileName);
        Info.UploadDuration.Stop();
        return result;
    }

    return null;
}
```

**Flow:** `DoUpload` first tries `CheckUploadFilters` — the first matching `UploaderFilter.IsValidFilter(fileName)` replaces the configured destination entirely (`return true` short-circuits the switch). Otherwise the destination enum indexes the static factory registry. Before any network call: `CheckConfig` fails → `GetInvalidConfigResult` returns a non-null UploadResult carrying "configuration is invalid" **and raises** `OnUploadersConfigWindowRequested` so the user can fix settings mid-task (:1020). A valid service builds the uploader instance, wires progress + early-copy + error title + buffer size, then times the upload with a Stopwatch into `Info.UploadDuration`.
**Invariant:** configuration problems are results with error entries, not thrown exceptions — the retry ladder and terminal-status logic stay in charge. The uploader instance is stored on the task field (`uploader`) precisely so `Stop()` can call `StopUpload()` on it from another thread.
**Probe:** byte-exact probe GREEN pre-write: `if (!service.CheckConfig(Program.UploadersConfig))` → 3 matches (UploadData :886, ShortenURL :974, ShareURL :995) — the same gate shape across all three destination kinds.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "sharex", function_name: "sharex.ShareX.WorkerTask.WorkerTask.UploadData", direction: "inbound", depth: 1 });
```
Observed: callers are `UploadImage`, `UploadText`, `UploadFile`, and `CheckUploadFilters` — one choke point for all transports.

## Verdict
Adopt: single upload choke point, validate-before-build gate returning error-as-result, per-task override record threaded through the factory, and keeping the active transport reference for cancellation. Adapt the registry/factory to your DI style. Omit concrete services and the WinForms config-window request.
