<!-- capsule-v2 -->
# webhook-peer-validation-toctou — How do you stop webhook SSRF when DNS can rebind between check and connect?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A hostname passes a resolve-time safety check — why is that not enough, and what transport design closes the gap?

## Connect-time peer re-validation
**Path/Symbol:** `superset/reports/notifications/webhook.py` — `_raise_for_unsafe_peer` (:65-79), `_PeerValidating{HTTP,HTTPS}Connection` (:82-95), pools (:98-103), `_PeerValidatingHTTPAdapter` (:106-126), `_get_requester` (:129-147), `_validate_webhook_url` (:219-250).
**Signature:** `connect(self) -> None` (urllib3 override); `_get_requester() -> Any` (plain `requests` module or peer-pinned `requests.Session`).
**Data Shape:** escape hatch `ALERT_REPORTS_WEBHOOK_ALLOW_INTERNAL_HOSTS: bool`; `HTTPS_ONLY`, `TIMEOUT` config; adapter swaps `poolmanager.pool_classes_by_scheme` for both schemes.

### Decisive source
```python
def _raise_for_unsafe_peer(conn: HTTPConnection) -> None:
    """``_validate_webhook_url`` resolves and checks the hostname once, ahead of
    time; the connection opened here is resolved independently and may reach
    a different address (DNS rebinding via a low-TTL record), so the check
    has to be repeated against the address actually connected to."""
    sock = conn.sock
    if sock is None:
        return
    peer = sock.getpeername()[0]
    if not is_safe_ip(ipaddress.ip_address(peer)):
        raise NotificationParamException("Webhook URL target host is not allowed.")

class _PeerValidatingHTTPSConnection(HTTPSConnection):
    def connect(self) -> None:
        super().connect()
        _raise_for_unsafe_peer(self)

class _PeerValidatingHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs) -> None:
        super().init_poolmanager(*args, **kwargs)
        # Assign a new dict rather than mutating the manager's dict in
        # place -- the attribute otherwise aliases urllib3's module-global
        # default scheme-to-pool-class mapping.
        self.poolmanager.pool_classes_by_scheme = {
            "http": _PeerValidatingHTTPConnectionPool,
            "https": _PeerValidatingHTTPSConnectionPool,
        }
```

**Flow:** pre-flight `_validate_webhook_url`: scheme must be http/https (https-only per config), hostname present, and unless the operator opted into internal targets, `is_safe_host(hostname)` → dispatch uses `_get_requester()`: opt-in ⇒ bare `requests` (no pinning); default ⇒ fresh Session with the peer-validating adapter mounted on both schemes → every pooled connection calls `super().connect()` then validates the **actual socket peer IP** post-handshake; an unsafe peer (e.g. 169.254.169.254) aborts before any request bytes are sent.
**Invariant:** The resolve-time check and the connect-time check are independent resolutions; only the second closes rebinding TOCTOU. Pool-class swap must replace the mapping dict wholesale (mutating in place would corrupt urllib3's module-global defaults). The opt-out flag must bypass *both* layers consistently.
**Probe:** `tests/unit_tests/reports/notifications/webhook_tests.py:514-537` pins rebound loopback/metadata peer rejected on `conn.connect()`; :540-556 pins public peer allowed; :579-599 pins both adapters mounted by default; :602-675 is the end-to-end regression: hostname check monkeypatched to pass yet POST to loopback still rejected.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "webhook unsafe peer validate connection dns rebinding internal hosts", limit: 10 });
```

## Verdict
Adopt two-layer validation (URL policy + per-connection peer IP) via transport-level connection-class substitution; adapt to your HTTP client's pooling API; omit urllib3 internals but keep the "replace dict, don't mutate" rule wherever pool registries are global. Coverage: whole file read directly (349L); direct tests read at :514-675; file `no_recorded_issue`.
