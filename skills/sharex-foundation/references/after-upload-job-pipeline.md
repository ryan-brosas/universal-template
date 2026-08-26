<!-- capsule-v2 -->
# After-upload job pipeline — in what order do URL post-processing actions run, and what gates the whole chain?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How should post-upload actions (rewrite, shorten, share, copy, open, QR) be sequenced so each sees the previous step's output exactly once?

## Ordered flag-driven chain entered only when a URL is expected and no error occurred
**Path/Symbol:** `ShareX/WorkerTask.cs:DoAfterUploadJobs` (:795-882); entry gate at `ThreadDoWork` tail (:350-356).
**Signature:** `private void DoAfterUploadJobs()`
**Data Shape:** mutates `Info.Result` (URL rewrite, ShortenedURL) in place; consumes `TaskSettings.AfterUploadJob` flags plus advanced settings (`ResultForceHTTPS`, `AutoShortenURLLength`, `ClipboardContentFormat`, `OpenURLFormat`).

### Decisive source
```csharp
if (Info.TaskSettings.UploadSettings.URLRegexReplace)
{
    Info.Result.URL = Regex.Replace(Info.Result.URL, Info.TaskSettings.UploadSettings.URLRegexReplacePattern,
        Info.TaskSettings.UploadSettings.URLRegexReplaceReplacement);
}

if (Info.TaskSettings.AdvancedSettings.ResultForceHTTPS)
{
    Info.Result.ForceHTTPS();
}

if (Info.Job != TaskJob.ShareURL && (Info.TaskSettings.AfterUploadJob.HasFlag(AfterUploadTasks.UseURLShortener) || Info.Job == TaskJob.ShortenURL ||
    (Info.TaskSettings.AdvancedSettings.AutoShortenURLLength > 0 && Info.Result.URL.Length > Info.TaskSettings.AdvancedSettings.AutoShortenURLLength)))
{
    UploadResult result = ShortenURL(Info.Result.URL);

    if (result != null)
    {
        Info.Result.ShortenedURL = result.ShortenedURL;
        Info.Result.Errors.Add(result.Errors);
    }
}
...
// clipboard copy uses format parser or Result.ToString(); OpenURL likewise; QR posted via threadWorker.InvokeAsync
```
Entry gate (`ThreadDoWork` tail): `!StopRequested && Info.Result.IsURLExpected && !Info.Result.IsError` — empty URL becomes an error message instead of running the chain.

**Flow:** regex-rewrite URL → force HTTPS → maybe shorten (explicit flag, dedicated job, OR automatic length trigger; ShareURL jobs are excluded from shortening) → maybe share (ShortenURL jobs excluded) → CopyURLToClipboard with user format string via `UploadInfoParser.Parse` fallback `Result.ToString()` → OpenURL same pattern → ShowQRCode **marshaled** to the UI context. The whole method is wrapped in try/catch that converts any action failure into an appended error message.
**Invariant:** order matters — rewrite/HTTPS normalize before shorten/share consume the URL; each stage reads the mutated `Info.Result`, never a local stale copy. Job-type exclusions (`!= TaskJob.ShareURL` / `!= TaskJob.ShortenURL`) prevent a shortener job from re-sharing itself. Post-upload failures degrade to error entries; they never throw past this method.
**Probe:** byte-exact probes GREEN pre-write: `uploader.EarlyURLCopyRequested += url =>` (:901, early-copy interplay) and ThreadDoWork tail read directly at :350-356.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "DoAfterUploadJobs URLRegexReplace ForceHTTPS AutoShortenURLLength", limit: 10, fields: ["signature", "name", "file"] });
```
Observed: `WorkerTask.DoAfterUploadJobs` :795-882 ranks first with `UploadInfoParser.Parse` adjacent.

## Verdict
Adopt: single ordered chain over one mutable result object, length-triggered auto-shortening, job-type self-exclusion, fail-soft per-stage errors. Adapt the concrete stages/format tokens to your domain. Omit QR-code window and toast integrations.
