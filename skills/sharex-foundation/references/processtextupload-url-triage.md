<!-- capsule-v2 -->
# ProcessTextUpload URL triage — when the pasted payload is a URL, who decides between downloading, shortening, sharing, or uploading it as text?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How do you convert one ambiguous text payload into exactly one upload action using only settings flags?

## Valid-URL three-way gate with early returns; folder-index special case; text as fallback
**Path/Symbol:** `ShareX/UploadManager.cs:UploadManager.ProcessTextUpload` (:157-193).
**Signature:** `public static void ProcessTextUpload(string text, TaskSettings taskSettings)`
**Data Shape:** in: arbitrary clipboard/dragged text + taskSettings with `UploadSettings.ClipboardUpload*` booleans; out: exactly one of DownloadAndUploadFile / ShortenURL / ShareURL / IndexFolder / UploadText.

### Decisive source
```csharp
if (!string.IsNullOrEmpty(text))
{
    string url = text.Trim();

    if (URLHelpers.IsValidURL(url))
    {
        if (taskSettings.UploadSettings.ClipboardUploadURLContents)
        {
            DownloadAndUploadFile(url, taskSettings);
            return;
        }

        if (taskSettings.UploadSettings.ClipboardUploadShortenURL)
        {
            ShortenURL(url, taskSettings);
            return;
        }

        if (taskSettings.UploadSettings.ClipboardUploadShareURL)
        {
            ShareURL(url, taskSettings);
            return;
        }
    }

    if (taskSettings.UploadSettings.ClipboardUploadAutoIndexFolder && text.Length <= 260 && Directory.Exists(text))
    {
        IndexFolder(text, taskSettings);
    }
    else
    {
        UploadText(text, taskSettings, true);
    }
}
```

**Flow:** trim → if URL-shaped, first matching flag wins (download contents → shorten → share), each via early return so at most one action fires → non-URL (or URL with no flags): if auto-index enabled AND the text is ≤260 chars AND literally an existing directory path, index it; otherwise upload as text with custom-text templating allowed (`allowCustomText: true`).
**Invariant:** exactly one dispatch per call — the early returns make flag precedence part of the control flow, not an else-if chain someone can reorder accidentally. The directory check is deliberately guarded by a length cap (260 = classic MAX_PATH) BEFORE hitting the filesystem, and falls through to plain text upload when it fails.
**Probe:** byte-exact probe GREEN pre-write: `if (taskSettings.UploadSettings.ClipboardUploadURLContents)` → 1 match at UploadManager.cs:165.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "process text upload valid URL download shorten share index folder", limit: 5 });
```
Observed rank 1: `UploadManager.ProcessTextUpload` (:157-193).

## Verdict
Adopt precedence-ordered early-return gates over ambiguous payloads and the cheap-guard-before-filesystem-check pattern for path-shaped text. Adapt the three URL actions and the 260-char cap to your platform's constraints. Omit the specific uploader services behind ShortenURL/ShareURL (covered by other capsules).
