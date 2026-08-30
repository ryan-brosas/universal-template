<!-- capsule-v2 -->
# Cloud browser control plane — how does a local agent session acquire and release a remote CDP browser over REST?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you add a hosted-browser option to a CDP agent without duplicating launch logic or leaking auth failures into the wrong error path?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/cloud/cloud.py` `CloudBrowserClient` (:27-104 create, :106-195 stop, :197-210 close) + `browser_use/browser/cloud/views.py` whole + integration point `browser_use/browser/session.py` `BrowserSession.on_BrowserStartEvent` :778-895.
**Signature:** `async create_browser(request: CreateBrowserRequest, extra_headers=None) -> CloudBrowserResponse`; `async stop_browser(session_id=None, extra_headers=None) -> CloudBrowserResponse`.
**Data Shape:** `CreateBrowserRequest` is extra='forbid' with aliased fields (`cloud_profile_id`, `cloud_proxy_country_code`, `cloud_timeout` 1..240, `enableRecording`) serialized via `model_dump(exclude_unset=True)` so unset = server-side default. Response carries `id/status/liveUrl/cdpUrl/timeoutAt/startedAt/finishedAt`. Errors split `CloudBrowserAuthError(CloudBrowserError)` for credential problems vs plain `CloudBrowserError`.

### Decisive source
```python
# cloud.py — two verbs only; PATCH carries an action body
url   = f'{self.api_base_url}/api/v2/browsers'          # create: POST
api_token = os.getenv('BROWSER_USE_API_KEY')
if not api_token:
    try:
        api_token = CloudAuthConfig.load_from_file().api_token   # fail-open read
    except Exception:
        pass
if not api_token:
    raise CloudBrowserAuthError('BROWSER_USE_API_KEY is not set. ...')
headers = {'X-Browser-Use-API-Key': api_token, ...}
if response.status_code == 401: raise CloudBrowserAuthError('... invalid ...')
elif response.status_code == 403: raise CloudBrowserAuthError('... subscription ...')
elif not response.is_success:
    try: error_msg += f' - {response.json()["detail"]}'
    except Exception: pass                              # detail extraction is best-effort
    raise CloudBrowserError(error_msg)
...
self.current_session_id = browser_response.id           # remembered for stop()/close()
# stop: PATCH f'{base}/api/v2/browsers/{session_id}' json={'action': 'stop'}
if response.status_code == 404:
    if session_id == self.current_session_id:
        self.current_session_id = None                  # clear BEFORE re-raising
    raise CloudBrowserError(f'Cloud browser session {session_id} not found')
```
```python
# session.py on_BrowserStartEvent — where the plane attaches
if self.browser_profile.use_cloud or self.browser_profile.cloud_browser_params is not None:
    cloud_params = self.browser_profile.cloud_browser_params or CreateBrowserRequest()
    cloud_browser_response = await self._cloud_browser_client.create_browser(cloud_params)
    self.browser_profile.cdp_url = cloud_browser_response.cdpUrl
    self.browser_profile.is_local = False
except CloudBrowserAuthError:
    raise                                               # taxonomy preserved upward
...
await asyncio.wait_for(self.connect(cdp_url=self.cdp_url), timeout=15.0)
except TimeoutError:
    # CancelledError bypasses connect()'s except Exception cleanup, so tear down
    # partial state here or future start() calls skip reconnection
```

**Flow:** start event → cloud gate (`use_cloud OR cloud_browser_params`) → auth ladder env → auth-file → AuthError(upsell URL) → POST with exclude-unset body → status triage 401/403→AuthError, other→Error(+detail) → session id remembered → `cdpUrl` written back into the profile with `is_local=False` → normal CDP connect path continues under a 15s guard → `close()` stops current session (fail-silent) then acloses the httpx client (idempotent).
**Invariant:** auth failures stay in `CloudBrowserAuthError` all the way up (the session handler's tail uses an isinstance guard to suppress the "local failed, try cloud" nudge exactly when the failure already WAS cloud); a 404 on stop must clear `current_session_id` before raising; `close()` must be safe to call twice.
**Probe:** `tests/ci/browser/test_cloud_browser.py` — pins header name/value from both auth sources, missing-key AuthError text, 401→AuthError mapping, `PATCH ... {'action': 'stop'}` wire shape, and 404 clearing semantics (6 client tests + 2 profile-property tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "CloudBrowserClient create_browser stop_browser CreateBrowserRequest on_BrowserStartEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-verb client shape, the env→file→fail auth ladder with a distinct auth-error subclass carrying remediation URLs, `exclude_unset` request dumps, and the write-cdpUrl-back-into-profile integration seam. Adapt endpoint paths, header name, timeout constants (30s HTTP / 15s CDP connect), and the free/paid timeout limits (15/240 min). Omit the product upsell copy and utm parameters. Direct tests exist and were executed green this pass; no coverage caveat beyond parse-partial files elsewhere.
