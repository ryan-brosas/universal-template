<!-- capsule-v2 -->
# Clipboard content-type ladder — in what order do you try clipboard payloads, and what happens when the clipboard itself fails?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How should one "upload clipboard" action triage image/text/file-list content and recover from transient clipboard locks?

## Fixed priority ladder Image→Text→FileDropList; ExternalException offers recursive retry
**Path/Symbol:** `ShareX/UploadManager.cs:UploadManager.ClipboardUpload` (:203-251) + settings-gated variant `ClipboardUploadMainWindow` (:260-273).
**Signature:** `public static void ClipboardUpload(TaskSettings taskSettings = null)`
**Data Shape:** reads WinForms clipboard state (`Clipboard.ContainsImage/ContainsText/ContainsFileDropList`); consumes taskSettings (never null after default fill); no return value.

### Decisive source
```csharp
if (Clipboard.ContainsImage())
{
    Bitmap image;

    if (HelpersOptions.UseAlternativeClipboardGetImage)
    {
        image = ClipboardHelpers.GetImageAlternative2();
    }
    else
    {
        image = (Bitmap)Clipboard.GetImage();
    }

    ProcessImageUpload(image, taskSettings);
}
else if (Clipboard.ContainsText())
{
    string text = Clipboard.GetText();

    ProcessTextUpload(text, taskSettings);
}
else if (Clipboard.ContainsFileDropList())
{
    string[] files = Clipboard.GetFileDropList().Cast<string>().ToArray();

    ProcessFilesUpload(files, taskSettings);
}
...
catch (ExternalException e)
{
    DebugHelper.WriteException(e);

    if (MessageBox.Show("\"" + e.Message + "\"\r\n\r\n" + Strings.WouldYouLikeToRetryClipboardUpload, ...) == MessageBoxResult.Yes)
    {
        ClipboardUpload(taskSettings);
    }
}
catch (Exception e)
{
    DebugHelper.WriteException(e);
}
```

**Flow:** probe Image first → else Text → else FileDropList; each hit hands off to its dedicated Process* triage method. Any `ExternalException` (clipboard locked by another process — the classic Windows CLIPBRD_E_CANT_OPEN) surfaces a Yes/No retry dialog; **Yes recursively re-enters ClipboardUpload with the same settings**. All other exceptions are logged and swallowed.
**Invariant:** the ladder is priority-fixed and first-hit-wins (an item that is both image and text uploads as image). Retry is user-consented and unbounded only insofar as the user keeps pressing Yes — the recursion re-probes the ladder from the top rather than resuming mid-ladder. Generic failures never propagate to the caller.
**Probe:** byte-exact probes GREEN pre-write: `catch (ExternalException e)` → UploadManager.cs:237; recursive `ClipboardUpload(taskSettings);` → :244 (second match at :271 is the non-viewer fallback branch of `ClipboardUploadMainWindow`, not a retry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "UploadManager ClipboardUpload ExternalException retry", limit: 5 });
```
Observed rank 1: `UploadManager.ClipboardUpload` (:203-251). (First attempt with generic "contains image text file drop list" vocabulary missed to `ClipboardHelpers` helpers — use manager+exception vocabulary.)

## Verdict
Adopt the fixed content-priority ladder, the alternative-getter escape hatch for flaky clipboard stacks, user-consented recursive retry scoped to the platform's transient clipboard exception type, and swallow-and-log for everything else. Adapt the three payload kinds and the dialog to your platform. Omit WinForms Clipboard wrappers.
