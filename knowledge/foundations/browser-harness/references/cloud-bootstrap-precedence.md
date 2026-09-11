<!-- capsule-v2 -->
# Cloud bootstrap precedence guard — when may a CLI auto-spawn a billed browser on the user's behalf?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Under which exact conditions does an agent-facing CLI bootstrap a cloud browser, and why must explicit local config veto it?

## Five-gate opt-in bootstrap
**Path/Symbol:** `src/browser_harness/run.py:_run-bootstrap/_local_chrome_listening/_explicit_cdp_configured/_cloud_auth_configured` (:364-390, :78-101).
**Signature:** gates: `not daemon_alive() and not _local_chrome_listening() and not _explicit_cdp_configured() and _cloud_auth_configured() and os.environ.get("BU_AUTOSPAWN")`.
**Data Shape:** `_explicit_cdp_configured` = bool of non-empty `BU_CDP_URL`/`BU_CDP_WS`; `_cloud_auth_configured` = key lookup succeeds (AuthError ⇒ False, never crashes); admin scripts (`start_remote_daemon(`/`stop_remote_daemon(` prefix) bypass all gates.

### Decisive source
```python
# Auto-bootstrap a cloud browser is opt-in via BU_AUTOSPAWN — BROWSER_USE_API_KEY alone
# is not enough, since the key is commonly set for unrelated reasons (profile sync,
# cloud API calls, parent agents managing their own session). An explicit BU_CDP_URL
# or BU_CDP_WS also blocks the spawn so we honour the precedence install.md promises.
```

**Flow:** read task from stdin → banner → unless cloud-admin script: five gates in order → all pass ⇒ start_remote_daemon() → finally ensure_daemon() → install helper trace wrappers → `exec(code, globals())`.
**Invariant:** An API key alone must NEVER trigger billing; documented endpoint overrides must also veto (else the daemon env's BU_CDP_WS gets overwritten and the user is "billed for a cloud browser they never asked for"); EMPTY string counts as unset (fresh-box path #277 preserved); live-daemon and local-Chrome fast paths short-circuit regardless of explicit config; the Chrome probe hits `/json/version` — bare TCP would let any squatter masquerade.
**Probe:** `tests/unit/test_run.py:60-236` — fires on headless+key+AUTOSPAWN; blocked by URL, WS, both-set, bad-stored-auth; empty-string doesn't block; short-circuits preserved; non-Chrome listener rejected.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "autos spawn cloud bootstrap", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the gate order (liveness → local capability → explicit-config veto → auth-present → hard opt-in flag) whenever automation might spend money. Adapt env names. Omit the exec-based runner but keep an admin-verb escape hatch.
