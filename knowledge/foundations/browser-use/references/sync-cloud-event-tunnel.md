<!-- capsule-v2 -->
# Cloud sync event tunnel — fail-silent telemetry POSTs gated by a device-flow auth state machine

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you stream product telemetry/observability events to a cloud backend from an agent runtime without ever letting network problems or auth states break the user's run?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/sync/service.py` (161 lines): `CloudSync.handle_event` (:29-55), `_send_event` (:57-105), `authenticate` (:145-161); `browser_use/sync/auth.py`: `DeviceAuthClient.authenticate` (:275-343), `get_headers` (:345-349), `clear_auth` (:351-357), `CloudAuthConfig.load_from_file/save_to_file`.
**Signature:** `handle_event(BaseEvent) -> None` — total function, never raises. Send gate: authenticated -> all events; else `allow_session_events_for_auth` -> all events while the device flow runs; else drop at debug level.
**Data Shape:** bubus `BaseEvent` pydantic models; wire format is a batch envelope `{'events': [event.model_dump(mode='json')]}` plus injected `device_id`; auth persisted as `cloud_auth.json` (`api_token`, `user_id`, `authorized_at`) under `CONFIG.BROWSER_USE_CONFIG_DIR`.

### Decisive source
```python
# session identity is mined from the stream itself, not passed in
if event.event_type == 'CreateAgentSessionEvent' and hasattr(event, 'id'):
    self.session_id = str(event.id)

# TEMP_USER_ID semantics: never clobber an explicit temp id (CLI sets it on purpose)
current_user_id = getattr(event, 'user_id', None)
if current_user_id != TEMP_USER_ID:
    setattr(event, 'user_id', str(self.auth_client.user_id))

async with httpx.AsyncClient() as client:
    event_data = event.model_dump(mode='json')
    if self.auth_client and self.auth_client.device_id:
        event_data['device_id'] = self.auth_client.device_id
    response = await client.post(f'{self.base_url.rstrip("/")}/api/v1/events',
                                 json={'events': [event_data]}, headers=headers, timeout=10.0)
    if response.status_code >= 400:
        logger.debug(...)            # log-and-drop; NEVER raise into the agent loop
except httpx.TimeoutException: logger.debug(...)
except httpx.ConnectError: pass           # offline is a normal steady state here
except httpx.HTTPError: logger.debug(...)
except Exception: logger.debug(...)       # total handler: telemetry cannot crash the run

# device flow: rewrite api host to frontend host so users see a human URL
verification_uri = device_auth['verification_uri'].replace(self.base_url, frontend_url)  # '//api.' -> '//cloud.'
token_data = await self.poll_for_token(device_code=..., interval=device_auth.get('interval', 5))
self.auth_config.api_token = token_data['access_token']; self.auth_config.save_to_file()
```

**Flow:** event bus publishes typed events -> `handle_event` checks enabled flag (`CONFIG.BROWSER_USE_CLOUD_SYNC`; disabled = silent no-op) -> captures `session_id` from the first CreateAgentSessionEvent -> picks send/drop by auth state -> `_send_event` stamps user_id/device_id and POSTs a one-element batch -> every failure path ends at debug logging or silence. Separate `authenticate()` runs the device flow: start_device_authorization -> print verification URL -> poll for token -> persist to disk; `clear_auth()` unlinks the file entirely rather than writing empty values.
**Invariant:** the tunnel is a TOTAL consumer — no exception can propagate to the emitter; 404/auth errors during login are user-facing warnings, network errors during login are silenced; bearer headers are added only when a token exists; disabled config short-circuits BEFORE any auth work; auth file removal (not empty overwrite) is the logout contract.
**Probe:** from repo root, construct `CloudSync(base_url='http://127.0.0.1:1')` with sync disabled and assert `handle_event` returns None without touching the network; verify `get_headers()` is `{}` when unauthenticated (executed this pass; output in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "CloudSync handle event send device auth token", file_pattern: "browser_use/sync/*", limit: 12 });
```

## Verdict
Adopt the four-state gate (disabled / authenticated / auth-in-progress / anonymous-drop) plus the never-raise consumer wrapper for ANY fire-and-forget telemetry plane; it decouples product analytics health from run health. Reuse batch-envelope `{events:[...]}` + device_id stamping when aggregating later. The device flow itself duplicates filesystem-device-auth RFC 8628 mechanics — port THAT capsule for the polling ladder; this capsule owns the gating and fail-silence.
