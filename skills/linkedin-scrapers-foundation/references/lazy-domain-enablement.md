<!-- capsule-v2 -->
# Lazy CDP domain enablement — which domains must be ON for your handlers to fire, and who wins when code and user disagree?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you guarantee an event handler actually receives events while never re-enabling a domain the USER configured with custom parameters?

## Handlers imply domains; manual always beats auto
**Path/Symbol:** `zendriver/core/connection.py:_register_handlers` (:588-639), `_update_manual_domain` (:641-669), `add_handler` module-form (:363-376).
**Signature:** `add_handler(event_type_or_module, handler)`; `_update_manual_domain(domain_name, action: 'enable'|'disable')`.
**Data Shape:** two lists: `enabled_domains` (auto, derived from live handlers) and `manually_enabled_domains` (user intent). Module-form registration walks the CDP module and attaches the handler to EVERY event class in it (skipping UPPER_CASE constants, types, builtins) — `tab.add_handler(cdp.network, fn)` ≈ 29 handlers (test-pinned count).

### Decisive source
```python
if domain_mod not in self.enabled_domains and domain_mod not in self.manually_enabled_domains:
    if domain_mod in (cdp.target, cdp.storage):
        continue                      # enabled by the browser by default — never touch
    self.enabled_domains.append(domain_mod)   # added BEFORE sending, else infinite loop
    await self.send(domain_mod.enable(), _is_update=True)
...
if domain_mod in self.enabled_domains:        # manual enable/disable OVERWRITES auto state
    self.enabled_domains.remove(domain_mod)
```

**Flow:** on every non-internal `send`, `_register_handlers` diffs desired domains (from handlers) against current: missing → `Domain.enable()` sent FIRST with bookkeeping pre-applied (so a failure during enable unwinds cleanly); orphaned domains (handlers removed) are pruned from the auto list but manual ones persist. Reconnect replays `_register_handlers` (called from `aopen`) because the BROWSER forgets enabled domains when the socket drops.
**Invariant:** a manually-enabled domain is NEVER auto-disabled even when its last handler disappears, and never auto-re-enabled with bare `Domain.enable()` (which would wipe custom `Fetch.enable` patterns — the exact bug `test_handler_wont_reenable_without_params` exists for: re-enabling without params makes the interception hang forever). `target`/`storage` are assumed always-on and skipped.
**Probe:** REAL tests — `tests/core/test_tab.py:422 test_handler_wont_reenable_without_params` (asserts `cdp.fetch not in tab.enabled_domains` mid-flight; hangs on regression), `:450 test_manual_disable_send`, `:460 test_auto_enable_domain`, `:233 test_add_handler_module_event` (29-handler count).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "_register_handlers manually_enabled_domains", limit: 5 });
```

## Verdict
Adopt: derive protocol-session state from declared interest, keep a separate manual-intent lane that always wins, replay derivation on reconnect, and treat always-on domains as no-ops. Adapt the always-on set to your protocol version. This is the general form of linkedin-private-api's dual-persona header split: session state owned by ONE chokepoint with explicit precedence. Coverage: directly test-pinned (four live tests).
