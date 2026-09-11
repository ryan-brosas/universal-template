<!-- capsule-v2 -->
# AppWorld auth manager — lazy supervisor credentials whose failures are CACHED until auth actually needs them

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you source per-app credentials from an external evaluation supervisor that may not be initialized yet, without breaking startup or retrying forever?

## Lazy-load flags latch even on failure; retry resets the flag exactly once at call time
**Path/Symbol:** `src/cuga/backend/tools_env/registry/registry/authentication/appworld_auth_manager.py` (`AppWorldAuthManager(BaseAuthManager)` :24, lazy properties :34-64/:126-153, `_fetch_token` :226-327, `TokenFetchError` :8-22).
**Signature:** `profile` property fetches `/supervisor/profile` ONCE and sets `_profile_loaded=True` even when the fetch returned None; `_get_account_passwords()` same pattern against `/supervisor/account_passwords` (dict of account_name→password, skipping blank entries); `_fetch_token(app_name, password) -> dict`.
**Data Shape:** passwords payload is a LIST of `{account_name, password}` items folded into a dict; token POST sends form data `{username, password}` where username is `profile["phone_number"]` for the `phone` app else `profile["email"]`.

### Decisive source
```python
# appworld_auth_manager.py:50-58 — one reset-and-refetch when auth REALLY needs it
def _try_get_profile_with_retry(self, max_retries=1):
    profile = self.profile            # may return None from the CACHED failure
    if profile is None and max_retries > 0:
        self._profile_loaded = False  # reset flag so the property refetches
        profile = self.profile
    if profile is None:
        logger.warning("...AppWorld supervisor may not be initialized. ...")
    return profile
```
And `_fetch_token` raises `TokenFetchError(message, status_code, response_body, url)` whose `detailed_message` lifts `response_body["message"]` → `"detail"` → fallback string — the SAME body.message→detail ladder as the registry error envelope.

**Flow:** constructor accepts base_url defaulting to the local supervisor port; profile/passwords are loaded lazily so service start never blocks on the benchmark harness; HTTP failures during lazy load produce loud boxed logging (status/url/method/body/request-body) but return None/{} WITHOUT raising — the failure is cached by the loaded-flag; when a real authenticated call happens, the retry ladder resets the flag once, and a second miss raises `ValueError` telling the operator to enter the AppWorld context manager with a valid task_id.
**Invariant:** never raise from lazy loading (startup must not depend on the supervisor); cache failures to avoid hammering an absent supervisor; give auth-time exactly ONE refetch; username selection is app-specific (`phone` → phone_number, everything else → email).
**Probe:** no dedicated suite for this class at HEAD — sibling `tests/test_auth/test_token_refresh.py` (:29-33 FakeAuthManager) pins the BaseAuthManager refresh contract it inherits; boxed-diagnostic behavior is eval-debug UX (coverage caveat).
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "AppWorldAuthManager _fetch_token TokenFetchError", limit: 5 });
```

## Verdict
Adopt the fail-cached-lazy + single-auth-time-retry shape for any optional credential source. Adapt endpoints/username rules to your harness. Omit the print-boxed diagnostics (product eval-debug surface) unless you also need human-in-the-loop eval debugging.
