<!-- capsule-v2 -->
# Checkpoint-restart bridge — how is a foreign-runtime session derived without trusting a half-written profile?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you turn source cookies into a validated derived profile for a different runtime, atomically?

## Bridge → validate → export → restart → revalidate → commit
**Path/Symbol:** `linkedin_mcp_server/drivers/browser.py:_bridge_runtime_profile` (:383), `_create_browser_locked` routing ladder (:631); env switches `_debug_skip_checkpoint_restart` (:104), `_debug_bridge_every_startup` (:114), `experimental_persist_derived_runtime` (:124).
**Signature:** `async def _bridge_runtime_profile(profile_dir, *, cookie_path, source_state, runtime_id, launch_options, viewport, persist_runtime) -> BrowserManager`.
**Data Shape:** Runtime identity = `login_generation` string in `source-state.json`; derived artifacts live under `<source>/runtimes/<runtime_id>/` (`runtime_profile_dir`, `runtime_storage_state_path`). Generation match requires runtime_state present AND `runtime_state.source_login_generation == source_state.login_generation`.

### Decisive source (commit ordering)
```text
clear_runtime_profile(...)            # wipe any stale derived dir FIRST
start → goto /feed/ → import_cookies(cookie_path)   # portable superset
_feed_auth_succeeds(browser)          # prove before anything persists
if persist_runtime:
    export_storage_state(state_path, indexed_db=True)   # CHECKPOINT
    browser.close() must CONFIRM, else raise BrowserShutdownUnconfirmedError
                                      # reopening a dir under live Chromium is
                                      # the corruption in miniature
    reopened.start() → _feed_auth_succeeds(reopened)    # POST-COMMIT VALIDATION
    write_runtime_state(runtime_id, source_state, state_path, ...)
                                      # generation recorded ONLY after the
                                      # reopened profile proved itself
Failure paths: BaseException → confirm close → clear_runtime_profile (cleanup
refusals logged, never mask the original error); BrowserShutdownUnconfirmedError
re-raised untouched — closing again reports fake success because the manager
already dropped handles, and deleting the dir under live Chromium is exactly
what the guard exists to prevent.
Routing ladder (_create_browser_locked): same runtime_id → use SOURCE profile;
persist off (default) → fresh bridge each startup, cookie-export path disabled
(_browser_cookie_export_path=None); generation matches + artifacts exist →
reuse derived profile, demoting AuthenticationError AND BrowserDowngradeError
to re-bridge (a container image moving BACKWARDS gets a dir its own older
browser wrote — on the SOURCE profile a downgrade must reach the user instead);
else full checkpoint-restart bridge.
```

**Flow:** foreign runtime detected → fresh bridge validates source cookies on a throwaway derived dir → optional persistence checkpoints storage state, hard-restarts Chromium on the derived dir, revalidates, then commits the runtime state → subsequent startups reuse the committed derived profile until the source login generation advances.
**Invariant:** The generation marker is written only after the REOPENED browser proved `/feed/`; a crash anywhere earlier leaves no marker, so the next startup re-bridges from scratch. Derived-profile failures are recoverable by construction; source-profile failures are terminal user-visible errors.
**Probe:** `grep -c 'export_storage_state' linkedin_mcp_server/drivers/browser.py` → 1; `grep -c 'checkpoint' linkedin_mcp_server/drivers/browser.py` → 4; direct tests: `tests/test_browser_driver.py::test_experimental_missing_derived_runtime_bridges_and_checkpoint_commits` (:322), `test_experimental_matching_derived_runtime_failure_rebridges_from_source` (:540), `test_experimental_reopen_start_failure_clears_runtime_dir` (:627).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_bridge_runtime_profile export_storage_state checkpoint restart", limit: 5 });
```

## Verdict
Adopt validate→checkpoint→restart→revalidate→commit ordering for deriving environment-specific state from a shared source credential. Adapt storage format to your platform's session shape. Omit Patchright-specific indexed_db export flags.
