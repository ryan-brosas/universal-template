<!-- capsule-v2 -->
# MCP manager server-set hygiene — why does the cleanup loop need dedupe, idempotent refresh, and a finally?

**Source:** OpenAI Agents Python MIT `main@fe45b415` (fixes 042d84a #4591 + 3e67155 #4586); Codebase Memory project `openai-agents-python`. **Question:** A manager holding the same server instance twice (or failing mid-cleanup) — what must the lifecycle do so disconnect is safe to run once or twice?

## Deduped registry + refresh-in-finally
**Path/Symbol:** `src/agents/mcp/manager.py`: `_unique_servers` (:568–576, identity-based `seen: set` preserving order) applied at registration (`self._all_servers = self._unique_servers(servers)` :203) and at every filtered subset (:299, :331); `_refresh_active_servers` (:424–431); `_cleanup_all` wraps its whole loop in try/finally calling the refresh (:367–392).
**Signature:** `def _unique_servers(servers: Iterable[MCPServer]) -> list[MCPServer]` (staticmethod).
**Data Shape:** `_all_servers` (registration order), `_active_servers` (currently usable), `_failed_servers` list + `_failed_server_set` (dedupe helper), per-server `_errors` dict.

### Decisive source
```python
# 042d84a: duplicate instances previously connected/cleaned TWICE
-        self._all_servers = list(servers)
+        self._all_servers = self._unique_servers(servers)

# 3e67155: a cancelled/failed cleanup left stale servers marked active
         except Exception as exc:
             ...
             self._errors[server] = exc
+        finally:
+            self._refresh_active_servers()

def _refresh_active_servers(self):   # (:424-431)
    if self.drop_failed_servers:
        self._active_servers = [s for s in self._all_servers if s in self._connected_servers]
    else:
        self._active_servers = list(self._all_servers)
```

**Flow:** register → dedupe by object identity (same server passed via multiple agents connects once) → connect with per-server failure recording (`_record_failure`, phase-tagged) → on ANY exit from the cleanup loop — including CancelledError propagation when not suppressed — recompute `_active_servers` from connection truth. Failure recording itself is idempotent via the set-check.
**Invariant:** Active-set membership must be DERIVED from connection state at boundary crossings, never incrementally decremented — incremental removal loses on partial failures and cancellation. Identity-dedupe at ingress beats equality checks (servers may be unhashable-by-value).
**Probe:** `grep -c "self._unique_servers(" src/agents/mcp/manager.py` → 4 (registration :203 + filtered subsets :299/:331/:562). Direct tests: `tests/mcp/test_mcp_server_manager_cleanup_state.py::test_cleanup_all_removes_cleaned_servers_from_active_servers` (:11), `test_manager_owns_repeated_server_instance_once` (:33), `test_cleanup_all_refreshes_active_servers_when_cancellation_propagates` (:49).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_unique_servers _refresh_active_servers _cleanup_all manager", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ingress-dedupe + derived-active-set + finally-refresh for any multi-resource lifecycle manager; adapt failure-recording shape; omit MCP transport details. Companion: `hosted-mcp-approval-callbacks` covers the approval plane of the same integration.
