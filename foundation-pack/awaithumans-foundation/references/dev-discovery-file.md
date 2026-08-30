<!-- capsule-v2 -->
# Dev Discovery File — how do server, SDKs, and dashboard coordinate ports and tokens with zero config?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the full lifecycle of `~/.awaithumans-dev.json` and which staleness trap catches porters?

## PID-liveness discovery with precedence ladder
**Path/Symbol:** `packages/python/awaithumans/utils/discovery.py` — `write_discovery/read_discovery/delete_discovery` (:76–160), `resolve_server_url/resolve_admin_token` (:163–217); TS mirror `packages/typescript-sdk/src/internal/discovery.ts` (memoized `_cached`, `_setDiscoveryCacheForTesting` hook).
**Signature:** `resolve_server_url(*, explicit_url=None) -> str`; `resolve_admin_token(*, explicit_token=None) -> str|None`.
**Data Shape:** `{url, host, port, pid, started_at, admin_token?}` at `~/.awaithumans-dev.json`; chmod 0600 whenever a token is written.

### Decisive source
```python
pid = data.get("pid")
if pid is not None and not _is_process_alive(int(pid)):
    logger.info("Discovery file ... stale (PID %d no longer running) — ignoring.", path, pid)
    with suppress(OSError):
        path.unlink(missing_ok=True)      # clean up so we don't re-check next time
    return None
```
Liveness probe itself is signal 0 semantics:
```python
try:    os.kill(pid, 0); return True
except ProcessLookupError: return False
except PermissionError:   return True     # exists but can't signal — treat alive
```

**Flow:** server binds ⇒ writes file (host `0.0.0.0`/`::` rewritten to `localhost` for CLIENT access; dev-only auto-generated admin_token included when operator didn't set one) → SDK/dashboard read it on every call AFTER env-var checks → graceful shutdown deletes it → crashed server leaves a corpse that readers detect-by-PID and delete. Resolution order everywhere: explicit arg → env (`AWAITHUMANS_URL`, `AWAITHUMANS_ADMIN_API_TOKEN`) → live discovery file → default (`http://localhost:3001` / None).
**Invariant:** discovery is DEV-grade only — production distributes `AWAITHUMANS_ADMIN_API_TOKEN` explicitly ("the discovery file isn't the right distribution channel for cross-host secrets"). Missing/unreadable file degrades silently to defaults; the server's 401 then tells the user what's missing.
**Invariant (TS twin):** cross-runtime means dynamic `import("node:fs/promises")` swallowed to `{}` in browsers/edge — plus a process-lifetime memoization that does NOT notice dev-server restarts (documented: restart your agent too). Python has no cache; it re-reads each call.
**Probe:** `packages/typescript-sdk/tests/discovery.test.ts` (precedence pins incl. explicit-beats-env-beats-discovery, cache injection); Python side exercised through client tests + CLI serve.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "resolve_server_url read_discovery discovery file", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt PID-liveness staleness detection WITH cleanup-on-read, localhost rewriting, permission-restricted token writes, and the four-step resolution ladder mirrored across languages. Adapt the file name/location. Omit the TS memoization unless you also port its test-injection seam.
