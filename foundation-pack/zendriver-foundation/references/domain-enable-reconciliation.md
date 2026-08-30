<!-- capsule-v2 -->
# domain-enable-reconciliation — when must the library send `Domain.enable` for the user, and when must it not?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are event-handler domains auto-enabled/disabled without fighting explicit user calls?

## Handlers imply enables; manual calls always win
**Path/Symbol:** `zendriver/core/connection.py:Connection._register_handlers` (:588-639) and `_update_manual_domain` (:641-669), invoked from `send()` (:572-578).
**Signature:** `async def _register_handlers(self) -> None`; `_update_manual_domain(self, domain_name: str, action: Literal["enable", "disable"]) -> None`.
**Data Shape:** two lists — `enabled_domains` (auto, handler-driven) and `manually_enabled_domains` (user-issued). Always-on exceptions: `cdp.target` and `cdp.storage` are enabled by default and never auto-enabled (:617-619).

### Decisive source
```python
# send(): enable is registered BEFORE the request, disable AFTER
if not _is_update:
    domain_name, _, action = tx.method.partition(".")
    if action == "enable":
        self._update_manual_domain(domain_name, action)
    await self._register_handlers()
    if action == "disable":
        self._update_manual_domain(domain_name, action)
```
and in `_register_handlers`, a failed auto-enable is rolled back:
```python
self.enabled_domains.append(domain_mod)
await self.send(domain_mod.enable(), _is_update=True)
except:  # noqa - ... we don't want an error before the "actual" request is sent
    self.enabled_domains.remove(domain_mod)
```

**Flow:** on each non-internal command: reconcile handlers→domains (enable any missing; drop domains whose last handler disappeared by sweeping a copy of `enabled_domains`), with manual `enable`/`disable` recorded around it. Manual state overwrites auto state (`_update_manual_domain` first removes the module from `enabled_domains`, then toggles `manually_enabled_domains`) — so an explicit user `disable` permanently suppresses re-enable for that domain. The `_is_update=True` flag prevents infinite recursion (auto-enables re-entering `send()`).
**Invariant:** every auto-enable is sent *before* the user's actual command so its events arrive; a rollback-on-failure keeps `enabled_domains` truthful. A port that registers domains after sending the command silently loses events for the first request.
**Probe:** direct tests pin add/remove handler behavior end-to-end through real event delivery: `tests/core/test_tab.py::test_add_handler_type_event` (:210), `test_remove_handlers_specific_event` (:259); static anchor `grep -c 'domain = "input_"' zendriver/core/util.py` → 1 shows the `input`→`input_` module-name shim used by this reconciliation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "_register_handlers enabled domains", limit: 5 });
```

## Verdict
Adopt the before/after ordering and the two-list model exactly; adapt the always-enabled set (`target`, `storage`) to whichever CDP version you target; omit nothing else — this subsystem has no host-specific parts.
