<!-- capsule-v2 -->
# Recent-task bounded queue — how do you keep a bounded "recent items" list thread-safe while persisting it to settings?

**Source:** ShareX GPL-3.0 `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`; Codebase Memory `sharex`. **Question:** Where does eviction, clamping, and persistence happen so a hot path (called after every task) never grows unbounded or deadlocks on UI refresh?

## Lock-guarded Queue with dequeue-while-full eviction and outside-the-lock settings write
**Path/Symbol:** `ShareX/RecentTaskManager.cs` (:32-151); hotspot fan-in 172 (`Add` is a graph top node).
**Signature:** `public void Add(WorkerTask task)` / `public void Add(RecentTask task)`
**Data Shape:** `Queue<RecentTask>`; `MaxCount` clamped 1..100; static `itemsLock`; side effect: `Program.Settings.RecentTasks` array (or null when saving disabled).

### Decisive source
```csharp
public void Add(WorkerTask task)
{
    string info = task.Info.ToString();

    if (!string.IsNullOrEmpty(info))
    {
        RecentTask recentItem = new RecentTask()
        {
            FilePath = task.Info.FilePath,
            URL = task.Info.Result.URL,
            ThumbnailURL = task.Info.Result.ThumbnailURL,
            DeletionURL = task.Info.Result.DeletionURL,
            ShortenedURL = task.Info.Result.ShortenedURL
        };

        Add(recentItem);
    }

    if (Program.Settings.RecentTasksSave)
    {
        Program.Settings.RecentTasks = Tasks.ToArray();
    }
    else
    {
        Program.Settings.RecentTasks = null;
    }
}

public void Add(RecentTask task)
{
    lock (itemsLock)
    {
        while (Tasks.Count >= MaxCount)
        {
            Tasks.Dequeue();
        }

        Tasks.Enqueue(task);

        UpdateTrayMenu();   // MainWindowIntegration.RefreshMenus() — inside the lock
    }
}
```

**Flow:** every completed task with non-empty info → project to a plain `RecentTask` snapshot (only persisted fields) → bounded enqueue under lock → tray menu rebuilt → settings snapshot written **outside** the lock. `MaxCount` setter also drains the queue down and rebuilds the menu under lock. `Clear()` nulls the persisted setting.
**Invariant:** eviction is dequeue-oldest *before* enqueue, keeping `Count <= MaxCount` at all times — no "evict after insert then trim" off-by-one. The queue projection is a value snapshot, so later mutation of the live WorkerTask can't corrupt history. The only work inside the lock is queue mutation + menu refresh; serialization of the whole queue happens unlocked.
**Probe:** byte-exact probe GREEN pre-write: `while (Tasks.Count >= MaxCount)` → 1 match at RecentTaskManager.cs:115.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sharex", query: "RecentTaskManager Add MaxCount Dequeue Enqueue", limit: 10, fields: ["signature", "name", "file"] });
```
Observed: both `Add` overloads plus `InitItems`/`Clear` cluster in RecentTaskManager.cs.

## Verdict
Adopt: clamp-on-set + evict-before-insert + snapshot projection + unlocked persistence write. Adapt the lock granularity if your menu refresh is expensive (consider moving it out), and the settings surface to your config store. Omit the WinForms tray integration.
