<!-- capsule-v2 -->
# Zero-downtime worker restart ladder — why does the replacement start BEFORE the old worker dies?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What is the exact bring-up-before-retire sequence in `Multiprocess.restart_all`, and what happens when the replacement never becomes ready?

## Start-new → wait-ready → kill-old, per slot
**Path/Symbol:** `uvicorn/supervisors/multiprocess.py:Multiprocess.restart_all` (:172–194); readiness probe `Process.wait_until_ready` (:85–96); breaker in `keep_subprocess_alive` (:225–231).
**Signature:** `def restart_all(self) -> None` / `def wait_until_ready(self, timeout: float, should_exit: threading.Event | None = None) -> bool`.
**Data Shape:** Pipe-based healthcheck: parent `parent_conn.send(b"ping")`, child thread answers `self.server.started:bool`; `None` answer = no reply within timeout.

### Decisive source
```python
# :173-194 — one slot at a time, new before old
for idx, old_process in enumerate(self.processes):
    if self.should_exit.is_set():
        return
    new_process = Process(self.config, self.sockets)
    new_process.start()
    if not new_process.wait_until_ready(self.config.timeout_worker_healthcheck, self.should_exit):
        new_process.kill(); new_process.join()
        if not self.should_exit.is_set():
            logger.error(f"New child process [{new_process.pid}] was not ready in time; "
                         f"keeping worker [{old_process.pid}] and aborting the restart.")
        return                      # ABORT whole restart; old fleet stays up
    old_process.terminate()
    old_process.join()
    self.processes[idx] = new_process
```

**Flow:** for each slot: spawn replacement (shares the SAME inherited listening socket) → poll readiness via ping/pong pipe until `server.started` or deadline (`timeout_worker_healthcheck=5s`) → only then SIGTERM the veteran and join it → swap into the list. A failed/late replacement is killed and the ENTIRE rotation aborts with the old workers untouched. The main loop also auto-replaces dead workers every 0.5s tick — EXCEPT when exitcode == 3 (`STARTUP_FAILURE`: config/bind broken ⇒ stop the parent rather than hot-loop).
**Invariant:** At most N+1 processes exist transiently and capacity never drops below N−0 during rotation (old keeps serving while new warms). Readiness means "server.finished startup", NOT "answered any request". TTIN/TTOU resize by append/pop with the same Process wrapper; TTOU refuses to go below 1.
**Probe:** from the uvicorn checkout root: `bash -c "grep -cE 'new_process.wait_until_ready|old_process.terminate' uvicorn/uvicorn/supervisors/multiprocess.py"` → 2; `bash -c "grep -c 'exitcode == STARTUP_FAILURE' uvicorn/uvicorn/supervisors/multiprocess.py"` → 1; behavioral pins: `tests/supervisors/test_multiprocess.py:test_multiprocess_restart_aborts_when_replacement_not_ready` :174 and `test_wait_until_ready_bails_on_shutdown_or_dead_worker` :190. REAL RUNNER: suite green (14 passed/1 skipped) at pin under borrowed venv.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"restart_all wait_until_ready replacement","limit":5,"detail":"ids"}` → rank#1 `restart_all` :173-194 + rank#3 its direct test line-exact.
**Verdict:** Adopt the start→wait→retire ladder and the STARTUP_FAILURE circuit-breaker verbatim — both encode production incident lessons. Adapt healthcheck transport (pipe here). Omit Windows SIGBREAK↔SIGTERM relay unless targeting win32.

