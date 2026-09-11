<!-- capsule-v2 -->
# Backend chord/chain failure propagation — how does one task's failure unblock every waiter?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** When a task inside a chain/chord fails, which other result ids must be marked so nothing waits forever?

## BaseBackend.mark_as_failure
**Path/Symbol:** `celery/backends/base.py:Backend.mark_as_failure` (:189-253), `_call_task_errbacks` (:255-303), `mark_as_done` (:181), chord fallbacks `fallback_chord_unlock` (:839) / `apply_chord` (:865); redis-native counter `celery/backends/redis.py:add_to_chord` (:555).
**Signature:** `mark_as_failure(task_id, exc, traceback=None, request=None, store_result=True, call_errbacks=True, state=FAILURE)`; chain walk uses a deque of signature dicts lifted into `Context` objects.
**Data Shape:** `request.chain` = list of remaining signature dicts; each may carry `options.task_id`, `options.group_id`, `'chord'`, `subtask_type == 'chord'` with `kwargs.body`.

### Decisive source
```python
# celery/backends/base.py:210-250 — the failure walk
chain_elems = deque(chain_data)
while chain_elems:
    chain_elem = chain_elems.popleft()
    chain_elem_ctx = Context(chain_elem)
    chain_elem_ctx.id = chain_elem_ctx.options.get('task_id')
    ...
    if (store_result and state in states.PROPAGATE_STATES
            and chain_elem_ctx.id is not None):
        self.store_result(chain_elem_ctx.id, exc, state, ...)
    if 'chord' in chain_elem_ctx.options:
        self.on_chord_part_return(chain_elem_ctx, state, exc)
    # A chord step completes only when its body does ... Descend into it
    # so the failure reaches that result (see issue #9674).
    if getattr(chain_elem_ctx, 'subtask_type', None) == 'chord':
        chord_body = (chain_elem_ctx.kwargs or {}).get('body')
        if chord_body is not None:
            chain_elems.append(chord_body)
if call_errbacks and request.errbacks:
    self._call_task_errbacks(request, exc, traceback)
```

**Flow:** mark the failing id → walk EVERY downstream chain element storing the propagated failure under ITS id (only for PROPAGATE_STATES and resolvable ids — anonymous complex signatures are skipped deliberately, uplifted chords cover them) → any element that is itself part of a chord gets on_chord_part_return so group counters decrement → chord-typed elements push their BODY onto the deque (#9674: the awaited result is the body's, not the chord wrapper's) → errbacks: arity-3+ callbacks run inline as functions `(request, exc, traceback)` with exception logging; single-arg legacy errbacks dispatch as an async group((task_id,)); NotRegistered errbacks fall back to async send.
**Invariant:** (1) Every skipped store must correspond to something that will be marked by another path — the comments document exactly which skips are safe. (2) mark_as_done mirrors this minimally: store + on_chord_part_return when request.chord. (3) Errback arity detection uses `__header__` presence + partial check to support bind=True errbacks. (4) ChordError creation preserves `__cause__` (`_create_chord_error_with_cause`).
**Probe:** `t/unit/backends/test_base.py::test_mark_as_failure_*` family within its 128 tests pins propagation; `t/unit/tasks/test_chord.py::test_unlock_ready_failed` (:108) pins body-failure unlock.
**Retrieve:**
```json
{"project":"ext-celery","query":"mark_as_failure on_chord_part_return chain errbacks","limit":5,"detail":"ids"}
```
## Verdict
Adopt the deque-walk with body-descent and the dual-mode errback dispatcher. Adapt Context reconstruction and PROPAGATE_STATES filtering to your result model. Omit backend-specific chord counters (redis INCR `.t`) unless you port that backend too.
