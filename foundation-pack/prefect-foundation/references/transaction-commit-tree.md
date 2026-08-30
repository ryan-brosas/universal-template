<!-- capsule-v2 -->

# Transaction commit-mode responsibility tree — Who commits a nested transaction, and what does stage() do after COMMITTED?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do EAGER/LAZY/OFF interact across parent/child transactions so results commit exactly once?

## Outermost-owner commit; stage is a no-op after COMMITTED

**Path/Symbol:** `src/prefect/transactions.py:BaseTransaction (67-257)`, `Transaction.__exit__ (270-297)`, `stage (231-247)`, `commit (335-391)`, `rollback (418-449)`; async twins `AsyncTransaction (452-654)`; entry points `transaction`/`atransaction (:661-763)`.

**Signature:** `Transaction(key=None, store=None, commit_mode=None, isolation_level=READ_COMMITTED, overwrite=False, write_on_commit=True, ...)` used as context manager yielding the txn.

**Data Shape:** States: PENDING → ACTIVE → STAGED → COMMITTED | ROLLED_BACK. `children: list[Self]` registered at reset-time; hooks accumulate via `+=`; `_stored_values` dict with deepcopy-on-read; `_holder` uuid4 identifies lock ownership.

### Decisive source
```python
def stage(self, value, on_rollback_hooks=None, on_commit_hooks=None):
    if self.state != TransactionState.COMMITTED:
        self._staged_value = value
        ...
        self.state = TransactionState.STAGED

def __exit__(self, *exc_info):
    ...
    if self.commit_mode == CommitMode.EAGER:
        self.commit()
    # if parent, let them take responsibility
    if self.get_parent():
        self.reset()
        return
    if self.commit_mode == CommitMode.OFF:
        # if no one took responsibility to commit, rolling back
        self.rollback()
    elif self.commit_mode == CommitMode.LAZY:
        # no one left to take responsibility for committing
        self.commit()
    self.reset()
```

**Flow:** enter → prepare (inherit commit_mode/isolation from parent when unset; validate SERIALIZABLE support against store else ConfigurationError) → begin: SERIALIZABLE acquires store lock keyed by txn key under `_holder`; if NOT overwrite and record EXISTS ⇒ state jumps straight to COMMITTED (cache hit — user fn will be skipped) → body runs (`call_task_fn` reads via txn when committed) → stage(value) on success → exit ladder: exception ⇒ rollback + rethrow · EAGER commits immediately · child with parent defers (parent takes responsibility) · OUTERMOST with OFF rolls back · outermost LAZY commits → commit recurses children first, runs on_commit_hooks, persists staged record (if write_on_commit), releases lock.

**Invariant:** (1) `stage()` after COMMITTED is deliberately a NO-OP — once the cache-hit short-circuit marked the txn committed, late staging must not clobber the stored value. (2) Commit/rollback recursion is depth-first over children; ROLLBACK hooks run in REVERSED registration order (LIFO undo semantics); a child's failure inside parent commit triggers parent rollback (`test_error_in_commit_triggers_rollback`). (3) Rollback of a child AFTER its parent reset propagates upward ("do this below reset so that get_transaction() returns the relevant txn"). (4) `get()` deep-copies stored values AND falls through to the parent scope for missing keys. (5) `transaction()` copies the store when metadata_storage is NullFileSystem to avoid inheriting it.

**Probe:** `grep -c 'state = TransactionState.COMMITTED' src/prefect/transactions.py` → 4; `grep -cF 'for hook in reversed(self.on_rollback_hooks):' src/prefect/transactions.py` → 2; `grep -c 'copy.deepcopy(self._stored_values' src/prefect/transactions.py` → 1. Direct tests: `tests/test_transactions.py:213 test_txns_dont_auto_commit`, `:225 test_txns_auto_commit_in_eager`, `:255 test_txns_commit_with_lazy_parent_if_eager`, `:266/:272 OFF-rolls-back / OFF-doesnt-if-committed`, `:278 error_in_commit_triggers_rollback`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "commit_mode lazy eager off rollback children", "limit": 4}'
```

## Verdict
Adopt the outermost-responsibility commit tree + cache-short-circuit begin for any staged side-effect framework; adapt persistence backend; omit ResultRecord plumbing details.
