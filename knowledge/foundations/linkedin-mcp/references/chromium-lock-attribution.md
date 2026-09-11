<!-- capsule-v2 -->
# Chromium SingletonLock attribution — is this profile actually in use?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you tell a live foreign holder of a browser profile from a crash leftover, across host boundaries?

## Parse the lock target; trust only same-host pids
**Path/Symbol:** `linkedin_mcp_server/session_state.py:profile_in_use_by()` (:645-737); `_exclusive_profile` (:739-800).
**Signature:** `profile_in_use_by(profile_dir: Path) -> Path | None`.
**Data Shape:** Returns None when free (INCLUDING stale locks from crashes); returns lock path when held. Of Chromium's three `Singleton*` links only `SingletonLock` encodes `<hostname>-<pid>`.

### Decisive source
```python
# The pid is only meaningful in that host's namespace, so it is probed only
# when the host matches ours. A lock from a *different* host — a container
# writing into the mounted auth root, most often — is treated as held: its
# pid says nothing to us, and the alternative is moving a profile out from
# under a running container. That errs toward refusing to rotate, which the
# operator can resolve by stopping the container, whereas the opposite
# corrupts two sessions silently.
```
Same host → `os.kill(pid, 0)` probes liveness (`ProcessLookupError` → stale → safe). Presence proves NOTHING — a crash leaves the link behind.

**Flow:** read `SingletonLock` symlink target → parse host-pid → foreign host → assume LIVE and refuse rotation → same host → signal-0 probe → alive = held, dead = stale.
**Invariant:** Three-signal exclusivity (all three checked across ALL profiles, not just source): (1) our own browser-open flag (kept deliberately when close was unconfirmed), (2) the refcounted cooperative lease (authoritative among cooperators), (3) Chromium's own SingletonLock catching FOREIGN holders. chrome-headless-shell never writes SingletonLock — precisely why the lease exists. Held across the WHOLE mutation: check-then-release leaves a window where another process launches Chromium mid-move.
**Probe:** `tests/test_session_state.py:516 test_lock_from_another_host_counts_as_held`, `:348 test_stale_lock_does_not_block_forever`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "profile_in_use_by SingletonLock exclusive profile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt host-gated pid probing with conservative foreign-host handling for any shared-profile or cross-namespace lock attribution. Adapt to other browsers' lock formats. Omit nothing.
