<!-- capsule-v2 -->
# Docker executor socket detection — podman → Rancher Desktop → default docker socket ladder

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How should container-backed code execution pick its daemon socket across developer machines without configuration, and what must the generated-code assembly look like for llm_sandbox sessions?

## _get_docker_client probes sockets in priority order
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/docker/docker_executor.py` (`DockerExecutor(RemoteExecutor)` :11, `_get_docker_client` :18-33, `execute_for_cuga_lite` :35-60 raises NotImplementedError, `execute_for_code_agent` :62-118).
**Signature:** constructor builds `docker.DockerClient(base_url=f"unix://{socket_path}")` eagerly; `execute_for_code_agent(wrapped_code, state, thread_id=None) -> str` returns stdout or an error STRING (never raises into the caller).
**Data Shape:** socket candidates: `/run/user/{uid}/podman/podman.sock` (rootless podman) > `~/.rd/docker.sock` (Rancher Desktop) > `/var/run/docker.sock` (default).

### Decisive source
```python
# docker_executor.py:87-96 + 99-107 — asyncio bridging is the porter trap
complete_code = f"""
{call_api_helper}

{variables_code}

{wrapped_code}

import asyncio
asyncio.run(_async_main())
"""
...
with SandboxSession(client=self.docker_client, image="python:3.12-slim",
                    keep_template=False, commit_container=False,
                    lang="python", verbose=True) as session:
    result = session.run(complete_code)
```
The wrapped agent code is async; llm_sandbox's `session.run` is sync — the injected tail wraps `_async_main()` in `asyncio.run(...)` because the container process has no running loop.

**Flow:** assemble remote `call_api` helper (via `CallApiHelper.create_remote_call_api_code`, see `call-api-helper-duality`) + formatted variables + user code + asyncio bridge → run in a throwaway `python:3.12-slim` sandbox (never committed, no template reuse) → non-zero exit ⇒ return stderr (or "Unknown error"); any exception ⇒ `"Error during Docker execution: {repr(e)}"`.
**Invariant:** cuga_lite mode deliberately REFUSES Docker (`NotImplementedError` naming local/E2B alternatives) — context_locals/tool serialization was never built here; silently falling back would produce code that cannot reach tools.
**Probe:** no dedicated unit suite at HEAD (Docker path needs a live daemon); behavior bounded by the executor-contract suites `test_execution_plan_wiring.py` / `test_tool_call_timeout.py` for sibling backends — coverage caveat recorded.
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "DockerExecutor execute_for_code_agent", limit: 5 });
```

## Verdict
Adopt the socket-probe ladder and the asyncio.run injection tail verbatim for any llm_sandbox-style host execution. Adapt image name and socket paths per environment. Omit cuga_lite-Docker support unless you also build context serialization — the NotImplementedError IS the contract.
