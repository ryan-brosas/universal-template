<!-- capsule-v2 -->
# Control panel mailbox — how do you remotely command workers over the broker?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How are remote-control commands registered, dispatched to a per-host node, and what does revoke/terminate actually do on each worker?

## Panel registry + _revoke + Pidbox
**Path/Symbol:** `celery/worker/control.py:Panel(UserDict)` (:46-77) with `@control_command` decorator (:69-77); `_revoke` (:214-247), `revoke_by_stamped_headers` (:160-212); mailbox transport `celery/worker/pidbox.py:Pidbox` (:19-73) and green twin gPidbox; client side `celery/app/control.py:Control.broadcast` (:755+).
**Signature:** decorator params `(name=None, alias=None, type='control'|'inspect', visible=True, default_timeout=1.0, help, signature, args, variadic)`; handlers receive `state` (AttributeDict: app/hostname/consumer/tset) first.
**Data Shape:** `Panel.data`: global dict command-name→function; `Panel.meta`: controller_info_t metadata for introspection. Mailbox node listens on a per-host reply queue; broadcasts use fanout.

### Decisive source
```python
# celery/worker/control.py:214-236 — revoke = flag + best-effort persist + optional kill
def _revoke(state, task_ids, terminate=False, signal=None, **kwargs):
    worker_state.revoked.update(task_ids)         # bounded LimitedSet
    for task_id in task_ids:
        try:
            state.app.backend.mark_as_revoked(
                task_id, reason='revoked', store_result=True)
        except Exception as exc:
            logger.warning('Failed to mark %s revoked in backend: %s',
                           task_id, exc)          # never fail the broadcast
    if terminate:
        signum = _signals.signum(signal or TERM_SIGNAME)
        for request in _find_requests_by_id(task_ids):
            ... request.terminate(state.consumer.pool, signal=signum) ...
            if len(terminated) >= size: break
```
```python
# celery/worker/pidbox.py:41-50 — every message advances the clock
def on_message(self, body, message):
    # just increase clock as clients usually don't
    # have a valid clock to adjust with.
    self._forward_clock()
    try:
        self.node.handle_message(body, message)
    except KeyError as exc:
        error('No such control command: %s', exc)
    except Exception as exc:
        error('Control command error: %r', exc, exc_info=True)
        self.reset()                              # resubscribe on handler crash
```

**Flow:** client broadcasts `{command, arguments, destination}` → broker fanout/reply-queue → Pidbox.on_message advances logical clock then dispatches through Panel.data → unknown commands log-and-continue; handler exceptions reset the node subscription. Revoke flags ids into the worker's bounded revoked set (strategy checks before execution) AND mirrors into the result backend so clients see REVOKED state even from workers that never saw the broadcast; terminate fans only into LOCALLY-known active requests (broadcasts may miss busy workers — documented semantics).
**Invariant:** (1) Backend marking failures must not fail the control reply — it's best-effort by explicit try/except. (2) The revoked set is BOUNDED (REVOKE_EXPIRES ~1h default): revokes are not permanent. (3) Clock forwarding on EVERY message (even no-ops) keeps Lamport ordering sane across nodes. (4) Panel.data is a class-level GLOBAL dict — registering a command mutates all workers in-process.
**Probe:** `t/unit/worker/test_control.py::test_revoke_*` family within 55 tests pins flagged/best-effort-backend/terminate paths; `t/unit/app/test_control.py` pins client-side broadcast.
**Retrieve:**
```json
{"project":"ext-celery","query":"Panel revoke _revoke mark_as_revoked Pidbox","limit":5,"detail":"ids"}
```
## Verdict
Adopt: decorator registry with metadata, clock-forward-on-message, best-effort backend mirroring, bounded revoke memory. Adapt kombu mailbox (reply queues/fanout) to your broker. Omit stamped-header group revokes unless you have message stamping.
