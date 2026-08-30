<!-- capsule-v2 -->
# Native messaging consume-once — how do you accept one-shot JSON file IPC from a browser extension without leaving stale requests behind?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How should a file-based request channel guarantee the request is consumed exactly once, even when parsing fails?

## Deserialize in try, delete the request file in finally; action switch with decode→download fallback
**Path/Symbol:** `ShareX/TaskHelpers.cs:HandleNativeMessagingInput` (:2444-2530); entry `ShareXCLIManager.CheckNativeMessagingInput` (:195-208).
**Signature:** `public static async Task HandleNativeMessagingInput(string filePath, TaskSettings taskSettings = null)`
**Data Shape:** in: path to a temp `.json` file holding a NativeMessagingInput {Action, URL, Text}; out: dispatched upload side effects. The file itself is always destroyed.

### Decisive source
```csharp
if (!string.IsNullOrEmpty(filePath) && File.Exists(filePath))
{
    NativeMessagingInput nativeMessagingInput = null;

    try
    {
        nativeMessagingInput = JsonHelpers.DeserializeFromFile<NativeMessagingInput>(filePath);
    }
    catch (Exception e)
    {
        DebugHelper.WriteException(e);
    }
    finally
    {
        File.Delete(filePath);
    }

    if (nativeMessagingInput != null)
    {
        ...
        switch (nativeMessagingInput.Action)
        {
            default: // TEMP: For backward compatibility
                if (!string.IsNullOrEmpty(nativeMessagingInput.URL))
                {
                    UploadManager.DownloadAndUploadFile(nativeMessagingInput.URL, taskSettings);
                }
                else if (!string.IsNullOrEmpty(nativeMessagingInput.Text))
                {
                    UploadManager.UploadText(nativeMessagingInput.Text, taskSettings);
                }
                break;
            case NativeMessagingAction.UploadImage:
                if (!string.IsNullOrEmpty(nativeMessagingInput.URL))
                {
                    Bitmap bmp = WebHelpers.DataURLToImage(nativeMessagingInput.URL);

                    if (bmp == null && taskSettings.AdvancedSettings.ProcessImagesDuringExtensionUpload)
                    {
                        try
                        {
                            bmp = await WebHelpers.DownloadImageAsync(nativeMessagingInput.URL);
                        }
                        catch
                        {
                        }
                    }

                    if (bmp != null)
                    {
                        UploadManager.RunImageTask(bmp, taskSettings);
                    }
                    else
                    {
                        UploadManager.DownloadAndUploadFile(nativeMessagingInput.URL, taskSettings);
                    }
                }
                break;
```

**Flow:** existence check → deserialize (failure only logs) → **finally deletes the file unconditionally**, so a corrupt request can never be retried into an infinite loop by a re-firing extension → null-input guard → action dispatch: legacy default (URL else Text), UploadImage with a three-rung ladder (data-URL decode → settings-gated download with silently swallowed failure → download-and-upload as file), UploadVideo/Audio/ShortenURL direct, UploadText.
**Invariant:** consume-once is enforced by `finally`, not by success: parse errors and missing fields still destroy the request file. Every branch independently re-checks its field for emptiness — the envelope's Action alone never authorizes a dispatch. Image handling degrades gracefully across rungs instead of failing.
**Probe:** byte-exact probe GREEN pre-write: `File.Delete(filePath);` → 1 match at TaskHelpers.cs:2460.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "native messaging input json deserialize action upload image URL", limit: 5 });
```
Observed rank 1/2 pair: `ShareXCLIManager.CheckNativeMessagingInput` (:195-208, .json-only gate) + `TaskHelpers.HandleNativeMessagingInput` (:2444-2530).

## Verdict
Adopt finally-block deletion for one-shot file IPC and per-branch field validation after an untrusted envelope deserialization. Adapt the transport (named pipes/sockets replace temp files) but keep the consume-once-on-parse-attempt semantics. Omit browser-extension manifest/native-host registration plumbing.
