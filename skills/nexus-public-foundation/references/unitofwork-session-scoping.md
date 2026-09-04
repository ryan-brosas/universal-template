<!-- capsule-v2 -->
# UnitOfWork thread-local session scoping — how do you scope a sequence of transactional methods to a thread without leaking sessions across callbacks, batches, or event broadcasts?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-transaction/.../UnitOfWork.java`); Codebase Memory `nexus-public`. **Question:** How do I implement ambient (thread-bound) transactional sessions so nested calls join the surrounding session, batched work reuses ONE session, and broadcasting events mid-transaction cannot leak the caller's context?

## Thread-local unit-of-work with three scopes
**Path/Symbol:** `public/common/components/nexus-transaction/src/main/java/org/sonatype/nexus/transaction/UnitOfWork.java` — `CURRENT_WORK` (:56), `Scope` enum (:58–62), `begin`/`beginBatch` (:95–109), `pause`/`resume` (:153–168), `openSession` (:211–226), `close` (:187–199), `doEnd`/`popWork` (:268–291).
**Signature:** `static void begin(Supplier<? extends TransactionalSession<?>> db)`; `static void beginBatch(...)`; `static UnitOfWork pause()`; `static void resume(@Nullable UnitOfWork pausedWork)`; `static TransactionalSession<?> openSession(@Nullable TransactionalStore<?> localStore, TransactionIsolation isolation)`.
**Data Shape:** `CURRENT_WORK` is a `ThreadLocal<UnitOfWork>`; each `UnitOfWork` carries a nullable `parent` link, the backing `TransactionalStore`, its `Scope` (`TRANSACTIONAL` = fresh session per operation | `UNIT_OF_WORK` = one lazily-opened shared session | `LOCAL_STORE` = short-lived scope auto-pushed for a store-local session), and the currently open `session`.

### Decisive source
```java
public static void resume(@Nullable final UnitOfWork pausedWork) {
  checkState(CURRENT_WORK.get() == null, "Cannot resume unit-of-work while other work is ongoing");
  if (pausedWork != null) {
    CURRENT_WORK.set(pausedWork);
  }
}

public static TransactionalSession<?> openSession(...) {
  UnitOfWork currentWork = CURRENT_WORK.get();
  if (localStore != null && (currentWork == null || currentWork.scope == UNIT_OF_WORK)) {
    // introduce a short-lived unit-of-work when we need to track a locally sourced session
    currentWork = new UnitOfWork(currentWork, localStore, LOCAL_STORE);
    CURRENT_WORK.set(currentWork);
  }
  else {
    checkState(currentWork != null, "Unit of work has not been set");
  }
  return currentWork.doOpenSession(localStore, isolation);
}

private void doEnd() {
  if (scope != UNIT_OF_WORK) {
    checkState(session == null, "Cannot end unit-of-work while transaction in progress");
  }
  popWork();          // restore parent (or remove) BEFORE closing
  doCloseSession();
}
```

**Flow:** `begin/beginBatch` pushes a new frame (refused while an inner transaction is in progress: `parent.session == null` guard in `doBegin`) → transactional interception calls `openSession(store, isolation)`: no current work ⇒ fail-fast `IllegalStateException`; LOCAL_STORE frames are auto-pushed when a specific store needs its own session under an outer UNIT_OF_WORK → `doOpenSession` opens the real session once per frame (batch scope keeps it across operations) and returns `this` as a wrapper so client `close()` is intercepted → `close()` closes the underlying session only when scope ≠ `UNIT_OF_WORK` and pops LOCAL_STORE frames automatically → event broadcasts wrap the critical section in `pause()`/`resume(work)` so listeners never see the caller's session → `end()` pops the frame then closes.
**Invariant:** the thread-local stack is strictly LIFO and pause/resume is all-or-nothing: `resume` refuses if any other work is ongoing (no silent overwrite), and ending a non-batch unit of work with an open transaction is a hard error. A porter who closes sessions eagerly in `finally` per-operation (instead of at `doEnd`) breaks batching; one who lets events inherit the caller's session leaks transactions into listener threads' semantics.
**Probe:** `nexus-transaction/src/test/java/org/sonatype/nexus/transaction/UnitOfWorkTest.java` — `testCanPauseNoWork` (:39), `testCannotResumeTwice` (:44), `testCannotStartTransactionWithNoWork` (:57); `TransactionalTest.java` — `testPauseResume` (:161), `testBatchTransactional` (:206), `testNested` (:240), `testNestedTransactionalStoreIsCaptured` (:330), `testCannotBeginWorkInTransaction` (:577).
**Coverage caveat:** none — this component has one of the richest direct suites in the repo.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "UnitOfWork beginBatch pause resume openSession", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-scope thread-local stack (fresh-per-op vs shared-batch vs store-local), the pause/resume handshake around out-of-scope callbacks, and the wrapper-session trick that turns client `close()` into scope-aware teardown. Adapt `TransactionalStore` to your storage SPI. Omit the Guava/javax specifics. Direct tests verified on-disk this pass at the pinned commit.
