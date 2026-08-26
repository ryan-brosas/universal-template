<!-- capsule-v2 -->
# Signal-queue supervisor loop — why does the parent enqueue signals instead of handling them inline?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** How does Multiprocess convert OS signals into named handlers, and why is the handler table method-name-derived?

## signal.signal appends to a list; the 0.5s loop dispatches by name
**Path/Symbol:** `uvicorn/supervisors/multiprocess.py:Multiprocess.__init__` (:150–158), `handle_signals` (:247–256), handler family `handle_{int,term,break,hup,ttin,ttou}` (:258–278).
**Signature:** `signal.signal(sig, lambda sig, frame: self.signal_queue.append(sig))` for every key in `SIGNALS`.
**Data Shape:** `SIGNALS = {getattr(signal, f"SIG{x}"): x for x in "INT TERM BREAK HUP QUIT TTIN TTOU USR1 USR2 WINCH".split() if hasattr(...)}` — name-suffix → signum map built defensively per-platform.

### Decisive source
```python
# :157 — handler body is ONLY an append (async-signal-safe minimal work)
for sig in SIGNALS:
    signal.signal(sig, lambda sig, frame: self.signal_queue.append(sig))
...
# :247-256 — drained from the main loop, not from signal context
def handle_signals(self) -> None:
    for sig in tuple(self.signal_queue):
        self.signal_queue.remove(sig)
        sig_name = SIGNALS[sig]
        sig_handler = getattr(self, f"handle_{sig_name.lower()}", None)
        if sig_handler is not None:
            sig_handler()
        else:
            logger.debug(f"Received signal {sig_name}, but no handler is defined for it.")
```

**Flow:** any handled signal → integer appended to a plain list (safe inside signal context) → the run-loop's 0.5s tick drains a TUPLE snapshot of the queue → each signum maps back to its NAME via the SIGNALS dict → dynamic lookup `handle_<lowercase-name>` executes if defined (HUP=rotate all, TTIN/TTOU=grow/shrink fleet, INT/TERM/BREAK=exit) else logs. Unhandled names (QUIT/USR1/USR2/WINCH) fall through to the debug branch.
**Invariant:** Real work never runs on the signal stack — only list append; this avoids reentrancy deadlocks when a handler would have taken locks the interrupted code holds. Snapshot-then-remove prevents mutation-during-iteration. Extending = add a `handle_x` method + ensure SIGX is in the name list.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'signal_queue.append(sig)' uvicorn/uvicorn/supervisors/multiprocess.py"` → 1; `bash -c "grep -c 'processes_num <= 1' uvicorn/uvicorn/supervisors/multiprocess.py"` → 1 (TTOU floor). Behavioral pins: `tests/supervisors/test_multiprocess.py:test_multiprocess_sig{term,break,hup,ttin,ttou}` :126–225. REAL RUNNER green at pin.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"signal queue handle hup ttin ttou","limit":5,"detail":"ids"}` → resolves `Multiprocess.handle_signals`, `handle_ttou` :274-278 line-exact.
**Verdict:** Adopt append-only signal capture + name-dispatched drain loop verbatim. Adapt the handler set to your platform matrix. Omit the win32 BREAK aliasing.

