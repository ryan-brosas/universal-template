<!-- capsule-v2 -->
# Deferred notification bus — how do you coalesce per-user notifications and delay them past an undo window without a queue table?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How are user notifications accumulated during a request, deduplicated across mediums, and flushed AFTER the "undo send" window closes?

## Subscription static event ledger
**Path/Symbol:** `app/Subscription.php:73` (`$occurred_events`), `:478-500` (`registerEvent`), `:311-455` (`processEvents`).
**Signature:** `registerEvent($event_type, $conversation, $caused_by_user_id, $process_now = false)`; `processEvents()` idempotent flush.
**Data Shape:** `$occurred_events[] = ['event_type','conversation','caused_by_user_id']` — a plain STATIC ARRAY on the model class; `$delay = now()->addSeconds(Conversation::UNDO_TIMOUT)` (15 s, Conversation.php:46 — must exceed the frontend floating-alert undo timer).

### Decisive source
```php
// app/Subscription.php:489-500 — every non-UPDATED/NEW event auto-appends UPDATED
if (!in_array($event_type, [self::EVENT_TYPE_UPDATED, self::EVENT_TYPE_NEW])) {
    self::$occurred_events[] = [
        'event_type'   => self::EVENT_TYPE_UPDATED,
        'conversation' => $conversation,
        'caused_by_user_id' => $caused_by_user_id,
    ];
}
// :407-424 — dispatch is DELAYED, on the emails queue
\App\Jobs\SendNotificationToUsers::dispatch($notify_info['users'], $notify_info['conversation'], $notify_info['threads'])
    ->delay($delay)
    ->onQueue('emails');
```
Flush triggers: HTTP requests via `TerminateHandler::terminate` (`app/Http/Middleware/TerminateHandler.php:16-19`) — Laravel middleware terminate runs AFTER the response is sent; console runs have no terminate, so `FetchEmails.handle` calls `Subscription::processEvents()` manually (FetchEmails.php:187-189 with the explaining comment).

**Flow inside processEvents:** for each recorded event → resolve mailbox users once per conversation (reuse across events via the `$notify[$medium][conv_id]` memo) → `usersToNotify` applies subscription filters: mute for non-direct events (:276-285), skip users who canSeeOnlyAssignedConversations but aren't assignee (#3843, :288-292), Eventy filter-outs → REMOVE the causing user from recipients (:337-343) → merge into per-medium buckets keyed by conversation → dispatch email jobs delayed by UNDO_TIMOUT; menu/browser notifications coalesce into one WebsiteNotification per conversation with user-id `unique()` merge across EMAIL/BROWSER/MEDIUM_MENU buckets (:420-443); browser push broadcast last.
**Invariant:** the actor never receives their own event's notification even when they triggered several; all mediums share ONE 15-second delay so "undo" can cancel everything; the static array means notifications are process-scoped state — CLI workers that enqueue nothing would silently drop them, hence the explicit fetch-command call. SendNotificationToUsers LISTENER (app/Listeners/SendNotificationToUsers.php:20-113) is the entry point: it maps domain event class → subscription EVENT_TYPE (skipping spam conversations for customer replies, imported threads entirely) then just registers — it NEVER notifies directly.
**Probe:** `grep -c "processEvents" app/Http/Middleware/TerminateHandler.php app/Console/Commands/FetchEmails.php | awk -F: '{s+=$2} END {print s}'` (= 2) and `grep -c "UNDO_TIMOUT" app/Conversation.php app/Subscription.php | awk -F: '{s+=$2} END {print s}'` (= 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "Subscription processEvents notify", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt request-scoped static accumulation + terminate-phase flush + single undo-window delay + per-conversation multi-medium coalescing; adapt the static array to a scoped container if your framework lacks terminate hooks (but keep the after-response timing); omit push-broadcast plumbing. Direct tests: none upstream.
