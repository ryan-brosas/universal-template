<!-- capsule-v2 -->
# Connect-time permission granting — how do you apply profile permissions exactly once per browser connection?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** where in the event lifecycle do requested permissions (camera, geolocation, clipboard) get granted, and what happens on failure?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/permissions_watchdog.py` whole (43L) — `PermissionsWatchdog.on_BrowserConnectedEvent` (:16).
**Signature:** `LISTENS_TO = [BrowserConnectedEvent]`; `EMITS = []`.

### Decisive source
```python
async def on_BrowserConnectedEvent(self, event) -> None:
    permissions = self.browser_session.browser_profile.permissions
    if not permissions:
        self.logger.debug('No permissions to grant'); return
    try:
        # Browser domain commands don't use session_id — grant applies browser-wide,
        # origin=None means grant to all origins.
        await self.browser_session.cdp_client.send.Browser.grantPermissions(
            params={'permissions': permissions}
        )
    except Exception as e:
        self.logger.error(f'❌ Failed to grant permissions: {str(e)}')
        # Don't raise - permissions are not critical to browser operation
```

**Flow:** browser connects → watchdog reads the declarative permission list from the profile config → single CDP `Browser.grantPermissions` call with no session scoping → failures logged and swallowed.
**Invariant:** grants fire exactly once on the connect event (not per-target), so re-attaching tabs never re-prompts; fail-open is deliberate — a denied permission list must never prevent a browsing session from starting.
**Probe:** deterministic source/graph probe only (coverage caveat: no dedicated test file; behavior pinned by LISTENS_TO contract + cited :30-:38).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "PermissionsWatchdog BrowserConnectedEvent grantPermissions browser_profile permissions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-shot connect-time granting with fail-open error policy; adapt the permission vocabulary to your platform; omit nothing — this is a complete minimal seam.
