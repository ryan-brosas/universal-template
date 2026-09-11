<!-- capsule-v2 -->
# Owner election — how does a frontend start or replace the daemon that owns the browser?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How should racing frontends elect one detached browser-owner, including stale owners and platform lock-handover differences?

## Election is two sides; Reach has three answers
**Path/Symbol:** `linkedin_mcp_server/daemon_election.py` (:1-1025; probe ladder :300-360); `Reach` enum; `linkedin_mcp_server/daemon_lock.py` platform split.
**Signature:** `compare(owner=..., frontend=...) -> Skew` (daemon_version); `_ask_to_stand_down(attachment)`; `DEFAULT_ELECTION_SECONDS = 90.0`, `_REACHABLE_SECONDS = 5.0`.
**Data Shape:** `Reach ∈ {ANSWERED, REFUSED, SILENT}`; `Skew ∈ {SERVICEABLE, OWNER_IS_STALE}`; buried-instance set per election.

### Decisive source
```python
class Reach(enum.Enum):
    """...Three answers rather than two, because "it did not answer" covers
    two situations that call for opposite reactions, and collapsing them is
    what made a healthy owner unreachable for a whole election.

    A process that is *gone* leaves a closed port, and the kernel refuses
    the connection at once. A process that is *stalled* still holds its
    listening socket, so the handshake completes into the backlog and the
    probe waits out its whole budget. Measured against the real probe:
    about ten milliseconds for the first, a full five seconds for the
    second. Three orders of magnitude apart, and the old ``bool`` threw the
    difference away."""
```
Platform split (module docstring): **POSIX** — frontend takes the lock FIRST, then hands an inheritable copy to the child (`DaemonLock.inheritable_copy`); taking it first removes the free-position window. **Windows** — a held lock cannot be handed over (20/20 measured), so the frontend takes NO lock and the child competes; every frontend waits for whoever wins to publish. And: the parent must let go before serving — both descriptors reference ONE locked open file description, so a kept original keeps the dead owner's lock alive, locking out all recovery.

Version-skew policy (daemon_version.py): newer frontend asks the owner to STAND DOWN then re-elects; older/same attaches (refusing wedges the client — it cannot take the lock, cannot start a replacement); unparseable versions are SERVICEABLE (local builds must not force restarts). `protocol_version` stays stricter (equality enforced by descriptor).

SILENT handling (:355-373): a silent endpoint is NOT buried — burying it made every later pass short-circuit so the healthy-but-stalled owner never got a second chance inside its own election; retries bounded by caller deadline, not retry count.

**Flow:** look up published owner → skip buried instances → version skew: OWNER_IS_STALE ⇒ stand-down request + bury + INCOMPATIBLE(re-elect=true) → reach(): ANSWERED ⇒ attach; SILENT ⇒ wait-and-retry within election budget; REFUSED ⇒ descriptor is leftovers ⇒ take lock / spawn detached owner / wait ≤90s for publish.
**Invariant:** Election timeouts must exceed twice the owner's startup allowance (test-enforced) so a slow machine isn't killed inside its own rules. Probe verdicts need three states; two collapse stalled-alive into gone-dead with opposite required reactions.
**Probe:** `tests/test_daemon_election.py` (2,352L) pins stand-down, burial, silent-retry; `tests/test_daemon_lock.py:463` pins Windows refusal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "Reach election stand_down look_up_owner", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt three-state probing, version-skew stand-down ladder, and the platform-split lock handover for any detached-daemon election. Adapt budgets. Omit LinkedIn tool surface details.
