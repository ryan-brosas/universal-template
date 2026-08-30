<!-- capsule-v2 -->
# Navigation readiness — lifecycle-event polling with loaderId staleness defense

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** when is a page actually ready to act on — and how do you avoid waiting on stale events from the PREVIOUS document load?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/session.py`: `_navigate_and_wait` (:1008-1130), adaptive timeout (:1030-1038), same-document detection (:1068-1075), readiness polling loop (:1076-1119); buffer source: `session_manager.get_lifecycle_events(target_id)` (per-target deque fed by ONE global `Page.lifecycleEvent` handler).
**Signature:** `_navigate_and_wait(url, target_id, timeout?, wait_until='load'|'domcontentloaded'|'networkidle'|'commit', nav_timeout=20) -> None | 'timeout...' status string`.
**Data Shape:** acceptable-event sets by level: networkidle always OK; +load for load/domcontentloaded; +DOMContentLoaded only for domcontentloaded; returns None on success, descriptive timeout string on failure.

### Decisive source
```ts
# ADAPTIVE default: same-domain navs get less patience (SPA route changes)
timeout = 3.0 if same_domain else 8.0
# Page.navigate wrapped in its own timeout — heavy sites block 10s+ here
nav_result = await asyncio.wait_for(Page.navigate({url, transitionType:'address_bar'}), nav_timeout)
if nav_result.get('errorText'): raise RuntimeError(f'Navigation failed: ...')
# SAME-DOCUMENT trap (#fragment, History API): navigate() omits loaderId and
# Chrome emits NO new load/DOMContentLoaded events — waiting would just burn the
# timeout against STALE events from the previous document. Detect & return early.
if not navigation_id: return None
lifecycle_events = self.session_manager.get_lifecycle_events(target_id)  # shared buffer!
while elapsed < timeout:
    for event_data in list(lifecycle_events):
        # stale-defense 1: event from a previous document carries the old loaderId -> skip
        if event_loader_id and navigation_id and event_loader_id != navigation_id: continue
        # stale-defense 2: loader-less events trusted only if AFTER nav started
        if not event_loader_id and event_data.get('timestamp', 0) < nav_start_time: continue
        if event_name in acceptable_events: return None
    await asyncio.sleep(0.05)
```

**Flow:** resolve session (no focus steal) → compute adaptive timeout (same-domain 3s vs new-domain 8s) → bounded Page.navigate → short-circuit for commit-level waits and same-document navigations → poll the per-target lifecycle buffer at 50ms until an event at-or-above the requested readiness level arrives with the CURRENT loaderId. Timeout returns a diagnostic string ('no lifecycle events received — monitoring may have failed') instead of raising, so callers can surface loading_status downstream.
**Invariant:** readiness is never inferred from sleep durations — only from Chrome's own lifecycle signals; two independent stale defenses (loaderId match, timestamp floor); the lifecycle buffer is owned per-target by SessionManager (a second attached target must never replace the feeding handler); failures are informative strings, not exceptions.
**Probe:** tests exercise same-document fast-path, cross-loaderId skipping, and the no-events diagnostic path via SessionManager's single global handler.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_navigate_and_wait wait_until lifecycleEvent loaderId networkidle same-document", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lifecycle-signal polling with loaderId/timestamp staleness guards and adaptive timeouts; treat readiness as data returned to callers. Adapt event names to host driver.
