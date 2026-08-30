<!-- capsule-v2 -->
# Conv-viewer presence registry — how do you show "who is viewing/replying" without websockets or a presence server?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How is live viewer state stored, expired, and surfaced to other agents — including the "is typing" flag?

## Cache-map heartbeat + sweeper command
**Path/Symbol:** cache key `conv_view` written by the conversation page JS via AJAX (shape: `[conversation_id][user_id] = ['t' => 'Y-m-d H:i:s', 'r' => 0|1]`); expiry in `app/Console/Commands/CheckConvViewers.php:39-88`; read-side `Conversation::getViewersInfo` (`app/Conversation.php:1952-2000`).
**Signature:** `check-conv-viewers` runs everyMinute with `withoutOverlapping()` (Kernel.php:68-70); `getViewersInfo($conversations, $fields, $exclude_user_ids)` static.
**Data Shape:** ONE global cache entry for ALL conversations, 20-min TTL; per-user heartbeat timestamps; `r=1` marks replying.

### Decisive source
```php
// app/Console/Commands/CheckConvViewers.php:53-74 — TTL expiry + realtime fan-out
$view_date = Carbon::createFromFormat('Y-m-d H:i:s', $data['t']);
if ($view_date && $now->diffInSeconds($view_date) > 25) {
    unset($cache_data[$conversation_id][$user_id]);          // remove viewer
    if (empty($cache_data[$conversation_id])) { unset($cache_data[$conversation_id]); }
    $need_update = true;
    \Cache::forget('conv_view_'.$user_id.'_'.$conversation_id);
    event(new \App\Events\RealtimeConvViewFinish([            // tell other viewers NOW
        'conversation_id' => $conversation_id, 'user_id' => $user_id,
    ]));
    \Eventy::action('conversation.view.finish', ...);
}
// Conversation.php:1968-1985 — reply flag wins over plain viewer
if (!empty($viewer['r']) && !in_array($user_id, $exclude_user_ids)) {
    $viewers[$conversation->id] = ['user' => null, 'user_id' => $user_id, 'replying' => true];
    break;                                                    // first REPLYING viewer only
}
```

**Flow:** browser heartbeats write `['t'=>now,'r'=>$replying]` while the agent keeps the conversation open → every minute the sweeper drops entries older than 25 s (heartbeat cadence must be <25 s) and broadcasts finish events → list/table renders call `getViewersInfo` which picks, per conversation, the first REPLYING viewer else the first viewer, then resolves user rows in ONE `User::whereIn(id)` query (:1987-1997) to avoid N+1.
**Invariant:** the registry is best-effort EPHEMERAL state — a dead client self-heals within ~25 s + one scheduler tick; nothing is persisted, so crashes lose only presence info. The 25-second constant pairs with the frontend heartbeat interval and with UNDO_TIMOUT-style alert loops (`fsFloatingAlertsInit close_after` comment at Conversation.php:44-46 documents a similar pairing). Read path deliberately returns `user=null` placeholders resolved later in bulk — do not hydrate inside the loop.
**Probe:** `grep -c "diffInSeconds" app/Console/Commands/CheckConvViewers.php` (= 3) and `grep -c "conv_view" app/Conversation.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "conv_view viewers", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt single-key cache map + timestamp TTL sweep + scheduled sweeper + bulk user hydration as the zero-infra presence pattern; adapt polling/broadcast transport to your stack (SSE/push); omit the RealtimeConvView event if you render presence only on page load. Direct tests: none upstream.
