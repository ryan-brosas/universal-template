<!-- capsule-v2 -->
# Folder-counter coalescing — how do list counts stay fresh under bursts without hammering the DB?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How are per-folder conversation counts recomputed so N rapid status changes produce O(1) recount jobs, and what does each folder type actually count?

## Cache-lock + queued job + hourly sweeper
**Path/Symbol:** `app/Folder.php:224-233` (`updateCounters`), `:235-275` (`updateCountersNow`), `app/Jobs/UpdateFolderCounters.php:33-49`.
**Signature:** `updateCounters()` → dispatch-or-inline; `updateCountersNow(): void` (persists via `$this->save()`).
**Data Shape:** cache lock key `"folder_update_lock_{id}"`, TTL 5 min; config `app.update_folder_counters_in_background` flips the whole plane to synchronous.

### Decisive source
```php
// app/Folder.php:224-233 — dedupe by cache lock, not queue size
if (config('app.update_folder_counters_in_background')) {
    if (!\Illuminate\Support\Facades\Cache::has("folder_update_lock_{$this->id}")) {
        \App\Jobs\UpdateFolderCounters::dispatch($this);
    }
} else {
    $this->updateCountersNow();
}
// app/Jobs/UpdateFolderCounters.php:33-41
if (Cache::has($this->lockKey)) { return; }            // another job is processing this folder
Cache::put($this->lockKey, true, now()->addMinutes(5));
try   { $this->folder->updateCountersNow(); }
finally { Cache::forget($this->lockKey); }
```
PORTER TRAP: the lock is checked at DISPATCH time and again at HANDLE time, but it is NOT an atomic mutex — two jobs for the same folder can pass handle-time check if the first hasn't cached the lock yet; correctness comes from idempotent recount + hourly `freescout:update-folder-counters` sweep (Kernel.php:57-58) healing any drift, not from strict once-only execution.

**Count predicates per folder type (updateCountersNow):**
- TYPE_MINE (per-user): active = published AND status=ACTIVE AND user_id=me in this mailbox; total = published only.
- TYPE_STARRED: count of `Conversation::getUserStarredConversationIds` — same value for BOTH counters.
- TYPE_DELETED: conversations with state=DELETED; both counters equal.
- isIndirect() (custom folders): rows in `conversation_folder` join table — drafts INCLUDED deliberately (state filter commented out).
- default folders: `conversations()` relation scoped by state PUBLISHED, active adds status ACTIVE.
An Eventy filter (`folder.update_counters`) can veto the whole recompute (:236-238).

**Invariant:** `active_count ≤ total_count` holds by construction on every branch; counters are DENORMALIZED copies — every mutation path must call `Mailbox::updateFoldersCounters()` (Mailbox.php:393-404 loops `$folders->each(updateCounters)`) or accept staleness until the next hourly job. Call sites: FetchEmails save paths (:1325,:1415), ConversationObserver created hook comment shows it's done MANUALLY ("Better to do it manually"), status-change events via UpdateMailboxCounters listener.
**Probe:** `grep -c "folder_update_lock" app/Folder.php app/Jobs/UpdateFolderCounters.php | awk -F: '{s+=$2} END {print s}'` (= 2) and `grep -c "updateFoldersCounters()" app/Console/Commands/FetchEmails.php` (= 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "updateCounters folder", limit: 5, fields: ["signature","name","file"] });
```
(rank#1 line-exact: `Folder.updateCounters app/Folder.php 224-233`.)

## Verdict
Adopt cache-key dispatch dedupe + finally-unlock + per-type counting predicates + scheduled reconciliation sweep; adapt the non-atomic lock to a real atomic flag ONLY if you also keep the sweeper; omit custom-folder join-table branches if you have no user-defined folders. Direct tests: none upstream.
