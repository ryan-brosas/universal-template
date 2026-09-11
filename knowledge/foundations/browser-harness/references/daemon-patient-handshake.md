<!-- capsule-v2 -->
# Patient handshake — why must a local CDP client stretch its WS opening handshake to human speed?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does a local daemon survive Chrome M144+'s consent-gated websocket upgrade without misclassifying it as a network failure?

## _PatientCDPClient open_timeout=45
**Path/Symbol:** `src/browser_harness/daemon.py:_PatientCDPClient/start-handshake-error-branching` (:92, :344-355, :511-529).
**Signature:** subclass of CDPClient overriding `start()` to pass `open_timeout=LOCAL_HANDSHAKE_TIMEOUT (45)` into websockets.connect; used ONLY when BROWSER_KIND == "local".
**Data Shape:** Before connecting locally the daemon logs `handshake-wait:` — admin.ensure_daemon greets this prefix (after a 2s quiet period) to print the Allow-popup hint and later classify timeout/403 handshake errors as permission-blocked rather than network failure.

### Decisive source
```python
class _PatientCDPClient(CDPClient):
    """CDPClient with the WS opening handshake stretched to LOCAL_HANDSHAKE_TIMEOUT."""

    async def start(self):
        import websockets
        if self.ws is not None:
            raise RuntimeError("Client is already started")
        connect_kwargs = {"max_size": self.max_ws_frame_size, "open_timeout": LOCAL_HANDSHAKE_TIMEOUT}
        if self.additional_headers:
            connect_kwargs["additional_headers"] = self.additional_headers
        self.ws = await websockets.connect(self.url, **connect_kwargs)
```

**Flow:** get_ws_url resolves → local kind logs handshake-wait hint BEFORE connecting → connect with 45s patience (a human must find and click Allow) → success proceeds to attach; failure branches on env/kind: BU_CDP_WS ⇒ remote-endpoint wording; local+timeout/403+toggle-on ⇒ `permission-blocked: ... wait for the user to click Allow`; else generic click-Allow message.
**Invariant:** A default-timeout client sees "timed out" during a consent wait and misroutes recovery to network debugging — the stretch converts human-speed approval into normal operation; the pre-connect hint line is load-bearing state machine input for the supervisor, not decoration.
**Probe:** No direct unit test for _PatientCDPClient (requires live WS) — coverage caveat; deterministic anchors verified at source :344-355; classifier side pinned by `tests/unit/test_admin.py:33-48` (timeout/403 ⇒ prompt; stale-ws noise ⇒ no prompt).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "patient handshake open timeout", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt stretching protocol handshakes whenever human consent can gate them. Adapt magnitude to your UX. Remote endpoints keep default timeouts — only consent-gated transports need patience.
