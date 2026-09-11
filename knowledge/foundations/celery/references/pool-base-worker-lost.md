<!-- capsule-v2 -->
# Pool base: WorkerLost conversion — how does a dead child become a routable failure instead of a hang?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What is the minimal pool contract, and how are child-process crashes converted into task-level errors?

## apply_target / BasePool
**Path/Symbol:** `celery/concurrency/base.py:apply_target` (:22-46); `BasePool` (:49-220) with state machine RUN=0x1/CLOSE=0x2/TERMINATE=0x3.
**Signature:** `apply_target(target, args=(), kwargs=None, callback=None, accept_callback=None, pid=None, getpid=os.getpid, propagate=(), monotonic=time.monotonic, **_)`; `BasePool.apply_async(target, args=None, kwargs=None, **options)` delegating to `on_apply`.
**Data Shape:** Pool capability flags on the class: `signal_safe`, `is_green`, `uses_semaphore`, `task_join_will_block=True`, `body_can_be_buffer=False` — the worker reads these to pick loop and shutdown behavior.

### Decisive source
```python
# celery/concurrency/base.py:22-45
def apply_target(target, args=(), kwargs=None, callback=None,
                 accept_callback=None, pid=None, ...):
    if accept_callback:
        accept_callback(pid or getpid(), monotonic())
    try:
        ret = target(*args, **kwargs)
    except propagate:
        raise                                   # WorkerShutdown/Terminate escape
    except Exception:
        raise
    except (WorkerShutdown, WorkerTerminate):
        raise
    except BaseException as exc:
        try:
            reraise(WorkerLostError, WorkerLostError(repr(exc)),
                    sys.exc_info()[2])
        except WorkerLostError:
            callback(ExceptionInfo())           # routed as task FAILURE
    else:
        callback(ret)
```

**Flow:** accept callback fires FIRST (this is what triggers `Request.on_accepted` → late-ack + task-started event) → target runs → normal return goes to `callback(ret)` which lands in `Request.on_success` → ANY non-Exception BaseException (SystemExit from a killed child, generator exit, etc.) is re-raised in place as `WorkerLostError(repr(exc))` AND delivered to the error callback as ExceptionInfo so the master-side request records failure. Shutdown exceptions (`WorkerShutdown`, `WorkerTerminate`) must escape untouched — they carry the child's cooperative shutdown intent.
**Invariant:** (1) The BasePool contract surface is: `start/stop/terminate/did_start_ok/flush/maintain_pool/grow/shrink/restart/terminate_job/on_*_timeout/_get_info` — a porter implementing a custom pool must honor all of them or guard with NotImplementedError like `terminate_job` does. (2) `did_start_ok()` gates startup: consumer raises `WorkerLostError('Could not start worker processes')` if the pool failed its first start (loops.py). (3) Out-of-tree pools register via env `CELERY_CUSTOM_WORKER_POOL` merged into ALIASES (`celery/concurrency/__init__.py`). (4) Callbacks must return fast — they run on the result-handler thread.
**Probe:** `t/unit/concurrency/test_concurrency.py::test_apply_target__raises_BaseException` (:76) pins the WorkerLost conversion; `test_interface_on_soft_timeout`/:144 pins the noop default timeout hooks.
**Retrieve:**
```json
{"project":"ext-celery","query":"apply_target BasePool WorkerLostError reraise","limit":5,"detail":"ids"}
```
## Verdict
Adopt: accept-before-run ordering, the BaseException→WorkerLost bridge with dual raise/callback delivery, and the shutdown-exception escape list. Adapt billiard specifics (fork, semaphore putlocks) to your process/thread model. Omit the `uses_semaphore`/`putlocks` machinery if your pool has internal slot accounting.
