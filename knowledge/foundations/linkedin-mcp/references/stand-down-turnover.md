<!-- capsule-v2 -->
# Stand-down turnover — how does a serving daemon give up its exclusive resource on request without wedging the lock?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you stop an owner that suppresses cancellation during teardown — and keep unauthenticated callers from pulling that trigger?

## In-route token check, noticed-in-one-place shutdown, hard-exit backstop
**Path/Symbol:** `linkedin_mcp_server/daemon_owner.py:create_owner_server` stand_down_route (:300), `_matches_token` (:246), `_serve_until_stopped` (:466), `_stop_within` (:537), `_exit_hard` (:575); constants `STAND_DOWN_PATH` (:243), poll/shutdown budgets (:452-463).
**Signature:** `async def _stop_within(serving: asyncio.Task[None], seconds: float) -> None`; `def _matches_token(presented: str, expected: str) -> bool`.
**Data Shape:** Stand-down request appends to a plain `turnover: list[str]`; the serve loop polls it at 0.1s. Route is part of the daemon protocol — a change REQUIRES `PROTOCOL_VERSION` bump (a frontend guessing wrong waits out its whole budget against a held lock).

### Decisive source
```text
Token check lives IN the route, not the auth middleware — measured on 3.4.4:
a custom route mounts OUTSIDE authentication middleware, so an unauthenticated
POST was served. Any local process (or any page the user's browser visits)
could otherwise stop the shared browser at will.
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer" or not _matches_token(presented, token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

_matches_token compares SHA-256 DIGESTS, not strings — hmac.compare_digest
REFUSES non-ASCII str arguments; "Bearer töken" would raise TypeError inside
the route and turn an unauthenticated request into a 500. Digesting also makes
the comparison length-independent.

Serve loop notices three exits in ONE place so an in-flight request gets its
reply first:
    wedged = stand_down_reason()      # unrecoverable owner wedge → exit IS the
                                      # recovery: kernel frees lock on exit
    if turnover: ...                  # newer build asked; graceful-but-bounded
    liveness.cancel_the_abandoned()   # same-tick dictionary scan, free
    quiet >= idle_timeout → exit      # process, not just browser: the next
                                      # election waits for the PROCESS, not the
                                      # Chromium it stopped running hours ago

The hard-exit backstop (_stop_within): wait_for(shield(serving), seconds);
on TimeoutError → logging.shutdown(); os._exit(1). Ending the WAIT is not
ending the PROCESS: asyncio.run cancels the pending task afterwards and waits,
UNBOUNDED, for cancellation to finish — and close_browser deliberately holds
cancellation until teardown ends (its cookie export is itself unbounded).
Measured before the fix: helper returned on time, process never left asyncio.run.

Startup failure path (0cd1e5f, #781/#789/#790): config-read failure logs the
diagnosis BEFORE handshake.fail() — a failed verdict is terminal (the frontend
may hard-stop the child as soon as it reads one) and an unhandled traceback
afterwards is not guaranteed anywhere visible; election-side _spawn now issues
a bounded hard stop for a child that reports failure yet stays alive, because
its inherited descriptor keeps the profile locked forever.
```

**Flow:** POST /control/stand-down with bearer token → route verifies in-route → sets turnover flag → reply returns FIRST → loop sees it → `server.should_exit=True` → uvicorn finishes in-flight requests + lifespan (which closes the browser) → bounded wait → hard exit if hung → kernel frees the daemon lock for the next election.
**Invariant:** Shutdown requests are never acted on mid-request, and no shutdown path may be unbounded: every wait has a wall-clock bound whose expiry path is process death, not another await.
**Probe:** `grep -c 'server.should_exit = True' linkedin_mcp_server/daemon_owner.py` → 4; `grep -c 'os._exit' linkedin_mcp_server/daemon_owner.py` → 1; direct tests: `tests/test_daemon_election.py` (:1895ff — unauthenticated/wrong-token POST refused, good token 200, "an unauthenticated caller stopped the daemon"), `tests/test_daemon_liveness.py:131`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "stand_down_route compare_digest stop_within should_exit", limit: 5 });
```

## Verdict
Adopt flag-polled graceful turnover with in-route authn and a hard-exit last resort for any daemon holding an OS-level exclusive resource. Adapt protocol-version discipline to your wire format. Omit uvicorn specifics.
