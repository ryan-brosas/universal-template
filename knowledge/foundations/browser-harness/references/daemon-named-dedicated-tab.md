<!-- capsule-v2 -->
# Named-daemon dedicated tab — how do parallel daemons share one browser without fighting over tabs?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** When several daemons attach to one Chrome, how does each keep its own tab — and what does the attach ladder reuse instead of always creating one?

## Dedicated-tab fork + five-rung page-reuse ladder
**Path/Symbol:** `src/browser_harness/daemon.py:Daemon.attach_first_page` (:371-452); classifiers `is_real_page`/`is_reusable_blank_page`/`is_inspect_tab`/`is_reusable_new_tab_page` (:309-341).
**Signature:** `async attach_first_page(replaces_session=None, enable_domains=True) -> target|None`.
**Data Shape:** default daemons + cloud (`REMOTE_ID`) browsers take the first-page path; named local daemons (`NAME != "default"` and not REMOTE_ID) get a dedicated tab tracked as `dedicated_target_id`.

### Decisive source
```python
if NAME != "default" and not REMOTE_ID:
    # parallel daemons on one browser would clobber each other's navigations
    pages_by_id = {t["targetId"]: t for t in targets if t["type"] == "page"}
    page = pages_by_id.get(self.target_id) or pages_by_id.get(self.dedicated_target_id)
    if page is None:
        async with self._dedicated_target_lock:      # narrow re-check
            refreshed = (await self.cdp.send_raw("Target.getTargets"))["targetInfos"]
            ...
            if page is None:
                tid = (await self.cdp.send_raw(
                    "Target.createTarget", {"url": "about:blank", "background": True}))["targetId"]
                self.dedicated_target_id = tid
```
Default-path rungs (in order): real pages → reusable about:blank (skipping `"Starting agent "` placeholders) → New Tab Page → TAKE OVER a leftover chrome://inspect recovery tab (navigate to about:blank, gated by a filesystem marker) → create about:blank in background.

**Flow:** classify targets → branch on named/local → re-attach existing dedicated tab first → under lock create replacement only when gone → attach flatten session → record replacement chain → enable domains.
**Invariant:** two concurrent stale-session recoveries must share ONE replacement tab (the lock re-fetches inside); shutdown deliberately leaves the dedicated tab open (`test_shutdown_leaves_dedicated_tab_open`).
**Probe:** `tests/unit/test_daemon.py:328` dedicated-tab creation; `:381` named remote keeps first-page; `:414` reattach keeps selected tab; `:434` replacement only when gone; `:452` concurrent reattach creates one replacement; `:537` shutdown leaves tab open.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "attach_first_page dedicated tab named daemon", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the dedicated-per-client tab model for any multi-agent browser sharing scenario and the reuse-before-create ladder; adapt the classifier URL lists; omit inspect-marker specifics if you have no permission-recovery flow. Six direct tests pin this seam.
