<!-- capsule-v2 -->
# ExecuteJobsafe-settings dispatch — how do you normalize untrusted per-workflow settings exactly once before a giant job switch?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** Where does caller-supplied workflow config get sanitized, and what does every switch branch rely on having received?

## One-time safe copy at switch entry; filePath-vs-picker duality inside branches
**Path/Symbol:** `ShareX/TaskHelpers.cs:TaskHelpers.ExecuteJob` (:77-392) + `ShareX/TaskSettings.cs:GetSafeTaskSettings` (:169-187).
**Signature:** `public static async Task ExecuteJob(TaskSettings taskSettings, HotkeyType job, string filePath = null)`
**Data Shape:** in: possibly-null/shared TaskSettings + HotkeyType + optional CLI filePath; out: fire-and-forget side effects (uploads started, windows opened). No result value.

### Decisive source
```csharp
public static async Task ExecuteJob(TaskSettings taskSettings, HotkeyType job, string filePath = null)
{
    if (job == HotkeyType.None) return;

    DebugHelper.WriteLine("Executing: " + job.GetLocalizedDescription());

    TaskSettings safeTaskSettings = TaskSettings.GetSafeTaskSettings(taskSettings);

    switch (job)
    {
        // Upload
        case HotkeyType.FileUpload:
            if (!string.IsNullOrEmpty(filePath))
            {
                UploadManager.UploadFile(filePath, safeTaskSettings);
            }
            else
            {
                UploadManager.UploadFile(safeTaskSettings);
            }
            break;
```
```csharp
// GetSafeTaskSettings — the two normalization branches
if (taskSettings.IsUsingDefaultSettings && Program.DefaultTaskSettings != null)
{
    safeTaskSettings = Program.DefaultTaskSettings.Copy();
    safeTaskSettings.Description = taskSettings.Description;
    safeTaskSettings.Job = taskSettings.Job;
}
else
{
    safeTaskSettings = taskSettings.Copy();
    safeTaskSettings.SetDefaultSettings();
}

safeTaskSettings.TaskSettingsReference = taskSettings;
return safeTaskSettings;
```

**Flow:** None-job early return → single `GetSafeTaskSettings` call → ~70-case HotkeyType switch where EVERY branch receives only `safeTaskSettings`. Normalization: default-flavored workflows are rebuilt from `Program.DefaultTaskSettings.Copy()` carrying over just Description+Job; custom workflows are copied then reset plane-by-plane via SetDefaultSettings. The original survives as `safeTaskSettings.TaskSettingsReference`.
**Invariant:** no switch branch ever mutates or trusts the caller's settings object — hotkeys, tray clicks, menus, and CLI all funnel here precisely so sanitization happens once. And roughly a dozen branches implement the same duality: a non-empty `filePath` routes straight to the file-taking overload; null/empty opens the interactive picker/dialog instead.
**Probe:** byte-exact probe GREEN pre-write: `TaskSettings safeTaskSettings = TaskSettings.GetSafeTaskSettings(taskSettings);` → 1 match at TaskHelpers.cs:83.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "ExecuteJob hotkey job dispatch safe task settings", limit: 5 });
```
Observed rank 1: `TaskHelpers.ExecuteJob` (:77-392); rank 2: `TaskSettings.GetSafeTaskSettings` (:169-187) — both halves of the seam on one page.

## Verdict
Adopt normalize-once-at-dispatch-entry (every branch can assume sanitized settings) and the optional-filePath branch duality for headless invocation. Adapt the case-per-hotkey switch to your command registry; the Copy()+reset semantics depend on your settings object supporting cheap deep copies. Omit WinForms dialog plumbing and localized logging details.
