<!-- capsule-v2 -->
# CLI command dispatch chain — how do you turn argv into uploads without a command table?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** How does a second process instance hand its arguments to the running app and get each one routed to the right subsystem?

## Ordered checker chain with empty-bodied ifs; named-workflow settings resolved once up front
**Path/Symbol:** `ShareX/ShareXCLIManager.cs:UseCommandLineArgs` (:46-76) + `FindCLITask` (:78-97) + `CheckCLIHotkey` (:129-155) + `CheckParameterForFilePath` (:157-172).
**Signature:** `public async Task UseCommandLineArgs(List<CLICommand> commands)`
**Data Shape:** in: parsed CLICommand list (Command verb + Parameter); out: side effects via UploadManager/TaskHelpers. `FindCLITask` returns a safe-normalized TaskSettings or null.

### Decisive source
```csharp
TaskSettings taskSettings = FindCLITask(commands);

foreach (CLICommand command in commands)
{
    if (command.IsCommand)
    {
        if (CheckCustomUploader(command) || CheckImageEffect(command) || await CheckCLIHotkey(command) || await CheckCLIWorkflow(command) ||
            await CheckNativeMessagingInput(command))
        {
        }

        continue;
    }

    if (URLHelpers.IsValidURL(command.Command))
    {
        UploadManager.DownloadAndUploadFile(command.Command, taskSettings);
    }
    else
    {
        UploadManager.UploadFile(command.Command, taskSettings);
    }
}
```
```csharp
// bad path parameter: logged, then the command is still CONSUMED
private string CheckParameterForFilePath(CLICommand command)
{
    if (command != null && !string.IsNullOrEmpty(command.Parameter))
    {
        string filePath = FileHelpers.GetAbsolutePath(command.Parameter);

        if (!File.Exists(filePath))
        {
            throw new FileNotFoundException();
        }

        return filePath;
    }

    return null;
}
// in CheckCLIHotkey:
catch (Exception e)
{
    DebugHelper.WriteException(e);
    return true;   // consumed despite failure
}
```

**Flow:** resolve ONE workflow TaskSettings up front by matching `-task <name>` against hotkey config (already passed through GetSafeTaskSettings) → per command: verbs go through the five-checker chain (custom-uploader import / image-effect import / hotkey-enum match / named workflow / native-messaging JSON), bare arguments triage URL-vs-file → non-matches fall through to plain file upload.
**Invariant:** the checker chain's empty-bodied `if (…) { }` is deliberate — each check fully owns its side effect and returns true when it consumed the command; ordering matters because checks are mutually exclusive by verb. A command that fails validation (missing file) is swallowed WITH log and never re-dispatched or queued.
**Probe:** byte-exact probe GREEN pre-write: `if (CheckCustomUploader(command) || CheckImageEffect(command) || await CheckCLIHotkey(command)` → 1 match at ShareXCLIManager.cs:58.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "command line arguments CLI upload workflow hotkey check", limit: 5 });
```
Observed rank 1/3: `ShareXCLIManager.CheckCLIWorkflow` (:174-193) + `CheckCLIHotkey` (:129-155); rank 2: `CLICommand.CheckCommand`.

## Verdict
Adopt the consume-or-fall-through checker chain, single up-front settings resolution shared across all args, and validate-and-consume error posture for headless invocations. Adapt the verb set and the enum-reflection hotkey matching (`Helpers.GetEnums<HotkeyType>()`) to your command vocabulary. Omit single-instance IPC plumbing that feeds this manager (out of seam scope).
