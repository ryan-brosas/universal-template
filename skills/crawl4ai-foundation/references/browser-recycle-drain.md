<!-- capsule-v2 -->

# Browser recycling: version-bump drain with refcounted contexts — How do you recycle a leaky browser after N pages WITHOUT killing crawls currently using it?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** How do you recycle a leaky browser after N pages WITHOUT killing crawls currently using it?

## Signature cache + LRU eviction + versioned drain

**Path/Symbol:** `crawl4ai/browser_manager.py:BrowserManager._make_config_signature (1392-1437), _evict_lru_context_locked (1439-1471), get_page (1542-1717), _maybe_bump_browser_version (1786-1908)`.

**Signature:** `sig_dict includes ONLY: proxy_config{server,username,password}, locale, timezone_id, geolocation{lat,lon,accuracy}, override_navigator, simulate_user, magic, _browser_version -> sha256(json, sort_keys)`.

**Data Shape:** Tracking dicts: contexts_by_config[sig]->ctx, _context_refcounts[sig]->int, _context_last_used[sig]->monotonic, _page_to_sig[page]->sig, sessions[session_id]->(ctx,page,last_used) TTL 1800s, _pending_cleanup[sig]->{version,done}. Caps: _max_contexts=20, _max_pending_browsers=3.

### Decisive source
```python
if len(self._pending_cleanup) >= self._max_pending_browsers:
                    self._cleanup_slot_available.clear()
                else:
                    ...classify sigs into active_sigs / idle_sigs by refcount...
                    for sig in active_sigs:
                        self._pending_cleanup[sig] = {"version": old_version, "done": done_event}
                    # Bump version — new get_page() calls will create new contexts
                    self._browser_version += 1
                    self._pages_served = 0
                    break  # exit while loop to do cleanup outside locks
            ...
            try:
                await asyncio.wait_for(self._cleanup_slot_available.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                # Force-clean any pending entries that have refcount 0
                # (they're stuck and will never drain naturally)
```

**Flow:** get_page: TTL sweep -> session hit? reuse -> build config signature (whitelist + current _browser_version) -> under _contexts_lock: reuse-or-create context, refcount++ INSIDE the lock, LRU-evict a ZERO-refcount oldest context when over cap (closed OUTSIDE the lock) -> new_page (failure rolls the refcount back under the lock before raising; persistent-context path serializes new_page behind _page_lock per GH-1198) -> register session -> pages_served++ -> maybe bump: threshold reached AND pending cap free -> active sigs parked in _pending_cleanup, version++, counter reset; idle sigs closed immediately -> release_page_with_context decrements; hitting 0 on a parked sig drains that old-version context and reopens a cleanup slot -> 30s slot-wait timeout force-cleans refcount-0 stragglers.

**Invariant:** (1) The signature MUST include _browser_version - that single field is what routes new requests to a fresh browser after a bump. (2) Refcounts mutate only under _contexts_lock; context.close() only ever runs outside it (closing inside deadlocks Playwright). (3) Idle sigs (refcount 0) are cleaned IMMEDIATELY at bump, never parked - no future release exists to trigger their drain. (4) Eviction scans oldest-first and SKIPS in-use contexts; all-active means no eviction, not eviction-of-victim. (5) Page-in-use tracking is GLOBAL keyed by normalized CDP endpoint (cdp:http://host:port) so two BrowserManagers on one browser never hand out the same page.

**Probe:** `tests/browser/` manager lifecycle suites + `tests/test_issue_1842_browser_none.py` (post-crash get_page contract)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "BrowserManager get_page context refcount recycle", "limit": 5}'
```

## Verdict
Adopt: whitelist signatures, inc-inside-lock/close-outside-lock, zero-refcount-only eviction, version-bump drain with capped pending set + timeout force-clean, and the shared page lock for persistent contexts. Adapt thresholds (20 contexts / 3 draining / 30s) and the signature field set to your context-affecting inputs. Omit the CDP connection cache if you never connect-over-cdp.
