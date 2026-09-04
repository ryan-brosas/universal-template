<!-- capsule-v2 -->
# FindDataType extension triage — when does a file path become an Image vs Text vs File task, and when is that decided?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How do you classify an upload payload by type without inspecting its content?

## Two settings-driven extension-set probes with File as the catch-all; evaluated at FACTORY time
**Path/Symbol:** `ShareX/TaskHelpers.cs:FindDataType` (:2060-2073); call sites `ShareX/WorkerTask.cs` :109, :189, :234.
**Signature:** `public static EDataType FindDataType(string filePath, TaskSettings taskSettings)`
**Data Shape:** in: path-or-filename string + taskSettings carrying `AdvancedSettings.ImageExtensions` / `TextExtensions` lists; out: EDataType enum {Image, Text, File}.

### Decisive source
```csharp
public static EDataType FindDataType(string filePath, TaskSettings taskSettings)
{
    if (FileHelpers.CheckExtension(filePath, taskSettings.AdvancedSettings.ImageExtensions))
    {
        return EDataType.Image;
    }

    if (FileHelpers.CheckExtension(filePath, taskSettings.AdvancedSettings.TextExtensions))
    {
        return EDataType.Text;
    }

    return EDataType.File;
}
```
```csharp
// CreateDownloadTask classifies BEFORE the download happens,
// using only the URL-derived filename:
string fileName = URLHelpers.URLDecode(url, 10);
fileName = URLHelpers.GetFileName(fileName);
fileName = FileHelpers.SanitizeFileName(fileName);
...
task.Info.DataType = TaskHelpers.FindDataType(task.Info.FileName, taskSettings);
task.Info.Result.URL = url;
```

**Flow:** probe the user-configurable image extension list → then the text extension list → everything else is File. Called from three factory sites: `CreateFileUploaderTask` (:109) and `CreateFileJobTask` (:189) classify real paths; `CreateDownloadTask` (:234) classifies the *predicted* filename of a not-yet-downloaded URL. The resulting DataType drives destination selection (`GetFileDestinationByDataType`) and the ProcessImagesDuringFileUpload job upgrade.
**Invariant:** classification is extension-only and settings-configurable (users can teach ShareX new types); content is never inspected at this stage. Because it runs in the factory, the decision is frozen before queueing — the worker kernel never re-classifies. Unknown extensions are safe: File is the terminal default, not an error.
**Probe:** byte-exact probe GREEN pre-write: `return EDataType.File;` → 1 match at TaskHelpers.cs:2072.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "FindDataType check extension image text file data type", limit: 5 });
```
Observed rank 1: `TaskHelpers.FindDataType` (:2060-2073); rank 2 is the HelpersLib `FileHelpers.FindDataType` twin — cite the ShareX-side one for task classification.

## Verdict
Adopt ordered extension-list triage with an explicit terminal default, executed once at task-construction time so downstream stages can trust the stamp. Adapt the two extension sets to be user-configurable if your tool accepts arbitrary files. Omit content-sniffing (deliberately absent here) and the legacy HelpersLib twin.
