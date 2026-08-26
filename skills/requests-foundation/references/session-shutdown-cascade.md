<!-- capsule-v2 -->
# Session shutdown cascade — what exactly happens when a Session exits its with-block or is closed?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** Who owns pool teardown when a Session dies — and what must each layer clear?

## Session.__exit__ / Session.close / HTTPAdapter.close
**Path/Symbol:** `src/requests/sessions.py:Session.__enter__` (:505-506), `.__exit__` (:508-509), `.close` (:883-886); `src/requests/adapters.py:HTTPAdapter.close` (:555-563).
**Signature:** `close() -> None` (both layers); graph trace: Session.close's sole internal caller is `Session.__exit__`.
**Data Shape:** `self.adapters: OrderedDict[prefix, BaseAdapter]`; adapter state is `poolmanager` plus `proxy_manager: dict[url, PoolManager]`.

### Decisive source
```python
# sessions.py
def __exit__(self, *args):
    self.close()

def close(self) -> None:
    """Closes all adapters and as such the session"""
    for v in self.adapters.values():
        v.close()

# adapters.py
def close(self) -> None:
    self.poolmanager.clear()
    for proxy in self.proxy_manager.values():
        proxy.clear()
```

**Flow:** with-block exit → `Session.close()` → one `close()` per mounted adapter → each adapter clears its direct PoolManager AND every cached per-proxy manager → urllib3 `.clear()` disposes pooled connections. Nothing at the Session level tracks or closes in-flight Responses; live streamed responses stay open unless their own close/consumption releases them.
**Invariant:** Shutdown ownership is strictly layered — the Session knows only the adapter list; it never touches pools directly, so custom mounts get torn down for free but ONLY if they subclass BaseAdapter and implement close(). Per-proxy managers are cleared individually because they are cached separately from the main poolmanager (adapter-pool-manager covers that caching); forgetting the loop leaks proxy connections after session close.
**Probe:** Direct test: `tests/test_requests.py::test_session_close_proxy_clear` (:2209-2218) patches two mock proxy managers into the http:// adapter and asserts EACH got `clear.assert_called_once_with()` after `session.close()`.
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "requests", function_name: "requests.src.requests.sessions.Session.close", direction: "both", depth: 3 });
```

## Verdict
Adopt the layered teardown contract (session iterates adapters; adapters clear main + proxy pools). Adapt pool-clearing to the host connection library's disposal API. Omit nothing — this seam is small but its omission is the classic keep-alive leak.
