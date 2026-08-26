<!-- capsule-v2 -->
# Pipe healthcheck ping/pong — how does the parent distinguish hung from ready workers without signals?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What exact protocol runs over the multiprocessing Pipe, and what does each failure shape mean?

## b"ping" → server.started:bool, with three distinct failure modes
**Path/Symbol:** `uvicorn/supervisors/multiprocess.py:Process._healthcheck` (:52–62), `ping/is_ready/pong/always_pong` (:64–80), daemon thread in `target` (:96–105).
**Signature:** `def _healthcheck(self, timeout: float) -> bool | None` (None = no/unreadable answer; True = started; False = not yet started).
**Data Shape:** `multiprocessing.Pipe()` duplex pair created in the PARENT before spawn; child side owned by a daemon thread running `always_pong()`.

### Decisive source
```python
# :52-62 — tri-state answer
def _healthcheck(self, timeout: float) -> bool | None:
    try:
        self.parent_conn.send(b"ping")
        if self.parent_conn.poll(timeout):
            started: bool = self.parent_conn.recv()
            return started
        return None                      # timed out = HUNG candidate
    except (OSError, EOFError, pickle.UnpicklingError):
        return None                      # dead/broken pipe = DEAD
```
```python
# :74-80 + :96-105 — child answers forever on a daemon thread
def pong(self) -> None:
    self.child_conn.recv()
    self.child_conn.send(self.server.started)
...
threading.Thread(target=self.always_pong, daemon=True).start()
self.server.run(sockets)
```

**Flow:** parent `ping(timeout)` sends a literal `b"ping"` then bounded-polls the pipe. Child's always-pong loop blocks on recv and replies with `server.started` — so `is_ready()` (True) gates zero-downtime rotation while `is_alive()/ping()` (not-None) only proves liveness for the reaper loop. Both pipe ends are closed explicitly in terminate()/kill() to unblock the child thread.
**Invariant:** The bool payload is read at ANSWER time — a worker that boots after its first ping correctly flips None→False→True across successive probes. The probe never raises into the supervisor; every transport failure collapses to None which callers treat as unhealthy.
**Probe:** from the uvicorn checkout root: behavioral pins `tests/supervisors/test_multiprocess.py:test_process_ping_pong` :43, `test_process_ping_pong_timeout` :49, `test_process_ping_broken_pipe` :54, `test_process_ready` :61 — REAL RUNNER green (14 passed/1 skipped) at pin under borrowed venv.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"healthcheck ping pong pipe worker startup flag","limit":5,"detail":"ids"}` → resolves `Process.ping`, `Process.is_ready`, and their direct tests line-exact.
**Verdict:** Adopt the tri-state ping/pong contract verbatim (None≠False is the whole point). Adapt Pipe→socketpair if spawn is unavailable. Omit pickle-error taxonomy beyond collapse-to-unhealthy.

