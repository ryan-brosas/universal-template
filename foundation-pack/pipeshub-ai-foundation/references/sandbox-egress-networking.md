<!-- capsule-v2 -->
# Dual-flag egress network gate — how does sandboxed code get internet without ever touching the caller's Docker network?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you let a sandbox reach PyPI/npm (and, opt-in, live APIs) while compose sibling services stay unreachable from sandboxed code?

## AND-gated flags onto ONE dedicated egress bridge
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/docker.py:DockerCodingSandbox.execute` (L253–254); `_run_container_sync` network branch (L532–541); `_install_packages_sync` (L618–702); `_ensure_egress_network` (L704–732).
**Signature:** `_ensure_egress_network(client) -> str`; container kwargs branch on `network_enabled = self._allow_network and request.allow_network`.
**Data Shape:** Backend ctor flag (`allow_network=False`) × per-request flag (`CodeRequest.allow_network=False`) → egress bridge name (`sandbox_egress`, ctor arg). Install phase ALWAYS uses the bridge; run phase only when both flags are true.

### Decisive source
```python
network_enabled = self._allow_network and request.allow_network   # BOTH must agree
...
if network_enabled:
    container_kwargs["network"] = self._ensure_egress_network(client)
    container_kwargs["network_disabled"] = False
else:
    container_kwargs["network_mode"] = "none"
    container_kwargs["network_disabled"] = self._network_disabled

def _ensure_egress_network(self, client):
    """Create (or reuse) the dedicated install-phase network... A user-defined
    bridge, never the caller's default Docker network, so sibling services on a
    compose deployment stay unreachable from the install container."""
    try:
        if client.networks.list(names=[name]):
            return name
        client.networks.create(name=name, driver="bridge", internal=False,
                               labels={"agent_loop.sandbox": "egress"},
                               check_duplicate=True)
    except Exception:
        # another process may have raced us to create it — re-list once
        if client.networks.list(names=[name]):
            return name
        raise
```

**Flow:** install: separate short-lived container on the egress bridge (pip `--target /deps` → extracted to host `deps_python/`; npm `--prefix /install` → `/install/node_modules` extracted to host `node_modules/`) → run: fresh container, no-network by default, joins the SAME bridge only when both flags allow → deps re-archived into later run containers with `PYTHONPATH=/deps` / `NODE_PATH=/node_modules[+image path]`.
**Invariant:** (1) Sandboxed code NEVER attaches to the daemon's default bridge — "internet for the sandbox" must not mean "line-of-sight to mongo/redis/postgres by service name". (2) The two-flag AND is the security boundary: either side alone vetoes; tests pin BOTH veto directions. (3) Egress-network creation races between processes resolve via list-recheck, not exception. (4) Installs land on the HOST working dir (extracted via archive), so they persist across calls like any other file — the install container itself is disposable.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_docker_coding_sandbox.py::test_default_run_container_has_no_network` (:321), `::test_backend_and_request_both_allowing_network_joins_egress_network` (:335), `::test_backend_flag_off_vetoes_request_allow_network` (:350), `::test_request_flag_off_vetoes_backend_allow_network` (:366).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_ensure_egress_network network_mode none sandbox_egress _install_packages_sync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dedicated-egress-bridge pattern + backend×request AND-veto for any containerized untrusted execution; adapt network/image names and registry URLs (ctor-injected). Omit PipesHub's adapter defaults. Direct tests pin all four flag combinations at HEAD. Test paths outside graph index at this pin — probes from on-disk reads.
