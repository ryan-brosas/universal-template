<!-- capsule-v2 -->
# Server role model + heartbeat liveness — who is this process, and is anyone still waiting for its call?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How should a multi-process tool server encode "which job this process does" without import cycles or config leakage, and how does it cancel work whose caller left?

## Role enum as process state, deliberately dependency-free
**Path/Symbol:** `linkedin_mcp_server/server_role.py` (:1-216); consumers `bootstrap` auth gates via `process_role()`.
**Signature:** `ServerRole ∈ {DIRECT, OWNER, PROXY}`; properties `.drives_browser` (DIRECT|OWNER), `.faces_a_client` (DIRECT|PROXY); `set_process_role(role)` raises `RoleAlreadyClaimedError` on conflicting second claim.
**Data Shape:** Module-level `_role: ServerRole | None = None` — `None` ≠ DIRECT ("nobody said" ≠ "somebody said single-process"); conflating them let a real DIRECT followed by an OWNER accept an impossible claim.

### Decisive source
```python
# Its own module, and deliberately free of imports from the rest of the
# package. ...an owner must not open a login window, a proxy must not take
# the profile lease... ``dependencies`` is one of them, and it cannot
# import from ``server``: ``server`` imports the tool modules, and those
# import ``dependencies``, so the edge would close the cycle.
#
# Deliberately not in AppConfig: that is settings a user chose, traveling
# over a pipe carrying exactly the fields both ends must agree on. The role
# is not one of them: an owner knows what it is, and being told by the
# frontend would be the wrong direction.
```
One process per MCP client is the stdio transport's doing — "who drives Chromium" is a property of the PROCESS, not the code.

**Flow:** entry point claims role once (conflict = refuse, not resolve) → deep stack asks `process_role()` where no server object exists → role gates login windows, lease acquisition, tool registration.

## Heartbeat-driven cancellation
**Path/Symbol:** `linkedin_mcp_server/daemon_liveness.py` (:1-347).
**Signature:** Frontend beats `GET /control/heartbeat` with header `x-linkedin-mcp-call: v1.<hex call id>` while waiting; owner cancels calls nobody waits for.
**Data Shape:** Marker version prefix `v1.` so unknown shapes are ignored whole, not half-read. Call ids bounded hex (HTTP-header-sourced dict keys on a long-lived process).

### Decisive source
```text
Measured: cancellation NOT forwarded across the loopback hop — client
answered at 0.66s, effect landed 0.7s later against a LinkedIn account
nobody watched. A running call looks exactly like a wanted one, so the
frontend says so REPEATEDLY and the owner cancels what nobody awaits.
No PROTOCOL_VERSION bump despite control-route change: a bump makes every
installed owner unreadable to a new frontend, and an unreadable owner
cannot be asked to stand down — upgrade breaks recovery itself. Optional
in both directions instead: new frontend vs old owner gets 404 and
proceeds; old frontend sends no marker and unmarked calls are NEVER
cancelled. Both directions tested.
```
**Flow:** proxy forwards call with fresh call-id header → heartbeat loop while client connected → heartbeats stop ⇒ owner cancels that call ⇒ result discarded.
**Invariant:** Compatibility shims beat version bumps when the bump breaks the recovery path itself; optional-in-both-directions fields keep mixed fleets working. Role identity belongs to the process, outside user config, claimed exactly once.
**Probe:** `tests/test_daemon_liveness.py` (997L) pins both compatibility directions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "ServerRole process_role heartbeat liveness cancel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the role-as-process-state pattern for any multi-role tool server; adopt heartbeat-liveness for proxied long calls. Adapt route/header names. Omit MCP transport specifics.
