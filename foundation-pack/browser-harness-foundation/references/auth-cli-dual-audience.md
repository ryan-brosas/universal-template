<!-- capsule-v2 -->
# CLI OAuth dual-audience flow — how does one login command serve both the agent (JSON) and the human (prose) without lying to either?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Cloud auth must be driven by an agent AND completed by a human — how is one command split into three paths with dual-format output?

## PKCE browser OAuth / device-code / manual key, each with json_output + prose
**Path/Symbol:** `src/browser_harness/auth.py:start_browser_auth` (:206-247), `complete_browser_auth` (:249-268), `start_device_auth` (:295-320), `complete_device_auth` (:323-346), `_callback_server` (:394-421), `_write_private_json` (:465-477), `run_auth_cli` (:508-543).
**Signature:** `browser_login(open_url=True, json_output=False, timeout=600)`; `device_login(...)`; `api_key_stdin_login(...)`.
**Data Shape:** `AuthRecord` (api_key + scopes/expiry/source); storage `auth.json` under `browser_use` key; secrets at rest 0600 by construction.

### Decisive source
```python
# Secrets at rest are 0600 BY CONSTRUCTION — os.open at CREATION time,
# never create-then-chmod (a window where the file is world-readable).
flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
with os.fdopen(fd, "wb") as f: f.write(raw)

# Dual-audience: agent pipes JSON, human gets prose that adapts to reality
if json_output:
    print(json.dumps({"status": "needs_user_auth", "auth_url": ..., "opened": ...}), flush=True)
else:
    print("Open this URL to sign in to Browser Use Cloud:")
    print(start.auth_url, flush=True)
    # "Waiting for login to complete..." vs "...after you open the URL"
    # depending on whether webbrowser.open() actually succeeded
```

**Flow:** browser path: PKCE pair → ephemeral localhost callback server → POST auth-start → open URL → poll `handle_request()` (0.5s timeout) → exchange code+verifier → store. Device path: POST device-start → poll token endpoint honoring `authorization_pending`/`slow_down` (interval += 5). Manual: getpass (tty) or stream read, length-heuristic ≥20.
**Invariant:** every flow has a `json_output` branch emitting machine-parseable state; humans never see a lie (prose adapts to whether the URL actually opened); the callback server closes in `except BaseException` on start-failure AND `finally` on completion; provider error/error_description re-raised verbatim so the user sees WHY.
**Probe:** `tests/unit/test_admin.py:258` `test_run_doctor_reports_bad_stored_cloud_auth_without_crashing` (adjacent); auth flow itself needs live network — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "pkce device_code callback server json_output", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the dual-audience split, three-path login, and 0600-by-construction secret writes for any CLI auth; adapt endpoints/client-id; omit nothing. Coverage caveat: live-network paths untested upstream.
