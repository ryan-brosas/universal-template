<!-- capsule-v2 -->
# Task admission concurrency gate — how do you bound concurrent uploads without a semaphore while keeping the pump self-healing?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** Where does concurrency limiting live so that a finished task immediately frees its slot for a queued one, including when the limit is disabled?

## Admission arithmetic recomputed on every completion
**Path/Symbol:** `ShareX/TaskManager.cs:StartTasks` (:96-119); re-dispatch from `Task_TaskCompleted` finally (:310-318).
**Signature:** `private static void StartTasks()`
**Data Shape:** reads shared `Tasks` list; inputs `Program.Settings.UploadLimit` (0 = unlimited), counts of `IsWorking` vs `InQueue` tasks; output = N calls to `WorkerTask.Start()`.

### Decisive source
```csharp
int workingTasksCount = Tasks.Count(x => x.IsWorking);
WorkerTask[] inQueueTasks = Tasks.Where(x => x.Status == TaskStatus.InQueue).ToArray();

if (inQueueTasks.Length > 0)
{
    int len;

    if (Program.Settings.UploadLimit == 0)
    {
        len = inQueueTasks.Length;
    }
    else
    {
        len = (Program.Settings.UploadLimit - workingTasksCount).Clamp(0, inQueueTasks.Length);
    }

    for (int i = 0; i < len; i++)
    {
        inQueueTasks[i].Start();
    }
}
```

**Flow:** `TaskManager.Start(task)` adds + wires events → `StartTasks()` fills free slots → each worker posts `TaskCompleted` back on the UI context → `Task_TaskCompleted` **finally** block calls `StartTasks()` again → freed slots admit queued tasks → if nothing is busy and the CLI holds an `AutoClose` command, `Program.Exit()` runs instead.
**Invariant:** the limit is *derived state recomputed at dispatch time*, not a held semaphore — a crashed/leaked slot is impossible because admission never depends on release bookkeeping; `Clamp(0, …)` makes over-limit settings degrade to "start none" instead of going negative.
**Probe:** no upstream test runner exists (13 csproj, zero test assemblies). Byte-exact source probe executed pre-write: `len = (Program.Settings.UploadLimit - workingTasksCount).Clamp(0, inQueueTasks.Length);` → exactly 1 match at `ShareX/TaskManager.cs:111`. GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "StartTasks UploadLimit InQueue working", limit: 10, fields: ["signature", "name", "file"] });
```
Observed: top hit `sharex.ShareX.TaskManager.TaskManager.StartTasks`, with `Task_TaskCompleted` :192-321 adjacent.

## Verdict
Adopt the recompute-on-completion admission pattern and the `0 = unlimited` sentinel with clamp-to-queue-length. Adapt the trigger surface (WinForms SynchronizationContext → your runtime's marshaler) and add locking if your task list is touched off-dispatch-thread. Omit tray/taskbar progress coupling and AutoClose exit behavior.
