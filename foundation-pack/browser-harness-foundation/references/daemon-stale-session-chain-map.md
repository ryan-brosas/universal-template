<!-- capsule-v2 -->
# Session-replacement chain — how does an in-flight request land on its ORIGINAL tab after a stale-session recovery?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** A CDP session id died while requests were queued against it; after re-attach, why is replaying onto the *current* session wrong, and how is the mapping maintained?

## Chain-preserving redirect map
**Path/Symbol:** `src/browser_harness/daemon.py:_record_session_replacement` (:494-505) consumed by `handle`'s stale-session branch (:628-665).
**Signature:** `_record_session_replacement(stale_session, replacement_session)`; map capped at 32 entries.
**Data Shape:** dict `{stale_session_id → replacement_session_id}`; values may themselves be stale keys whose entries were rewritten (chains).

### Decisive source
```python
# Preserve chains so requests delayed across multiple recoveries still
# land on their original tab, never whichever tab is current now.
for source, replacement in list(self._session_replacements.items()):
    if replacement == stale_session:
        self._session_replacements[source] = replacement_session   # rewrite tail
self._session_replacements[stale_session] = replacement_session
while len(self._session_replacements) > 32:
    self._session_replacements.pop(next(iter(self._session_replacements)))  # FIFO

# handle(): retry ONLY via the mapped replacement...
if replacement_session:
    return {"result": await self.cdp.send_raw(method, params, session_id=replacement_session)}
# ...explicit-session callers are NEVER silently redirected
if req.get("session_id"):
    return {"error": msg}
```

**Flow:** request fails with "Session with given id not found" → if caller pinned that exact session ⇒ loud error (no redirect) → else look up replacement map under `_session_state_lock`; on miss AND sid == current session, re-attach with `replaces_session=sid`, enable domains on the new session, then retry once through the mapped id.
**Invariant:** redirect goes ONLY through the recorded replacement for that exact stale session — never to `self.session`, which may have moved because the user switched tabs mid-flight. Recovery itself runs under the state lock so concurrent failures share one re-attach.
**Probe:** `tests/unit/test_daemon.py:705` `test_explicit_stale_session_is_not_redirected`, `:565` `test_delayed_stale_request_follows_recovery_during_domain_enable`, `:630` `test_tab_switch_waits_for_recovery_and_keeps_old_action_on_old_tab`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "stale session recovery explicit not redirected", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the chain-preserving map + explicit-session-no-redirect rule for any long-lived connection pool with server-side session recycling; adapt cap size/eviction; omit CDP specifics. Test-pinned at three points.
