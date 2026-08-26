<!-- capsule-v2 -->
# Transactional commit/retry ladder — when does a failing operation still COMMIT, which exceptions retry, and how do you swallow a commit failure without hiding the real cause?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-transaction/.../TransactionalWrapper.java`, `TransactionSupport.java`); Codebase Memory `nexus-public`. **Question:** How do I implement `@Transactional`-style semantics where the exception classes decide commit-vs-rollback, rollback-with-retry, and best-effort-commit — without losing the original business exception?

## The four-way exception matrix
**Path/Symbol:** `public/common/components/nexus-transaction/src/main/java/org/sonatype/nexus/transaction/TransactionalWrapper.java:proceedWithTransaction` (:45–118) + `instanceOf` (:120–129); spec defaults in `Transactional.java`; retry counting in `TransactionSupport.java:allowRetry` (:46–56).
**Signature:** `Object proceedWithTransaction(final Transaction tx)` driven by the `Transactional` spec arrays `commitOn()`, `retryOn()`, `swallow()`; `boolean instanceOf(Throwable, Class<?>...)` matches BOTH the throwable AND its direct cause.
**Data Shape:** loop state per attempt: `committed` (bool), `throwing` (the application throwable, may be null), `result`; `tx.reason(spec.reason())` set once outside the loop for audit; `retries` counter lives on the Transaction (`TransactionSupport`), reset to 0 on successful commit.

### Decisive source
```java
try {
  tx.begin();
  try {
    result = aspect.proceed();
    return result;
  }
  catch (final Throwable e) { // capture VM errors too (rethrown later)
    throwing = e;
  }
  finally {
    if (throwing == null || instanceOf(throwing, spec.commitOn())) {
      tx.commit();               // a listed business exception STILL commits
      committed = true;
    }
    if (throwing != null) {
      throw throwing;            // original cause always rethrown
    }
  }
}
catch (final Exception e) { // ignore VM errors here (no rollback/retry on them)
  if (!committed) {
    tx.rollback();
    if (instanceOf(e, spec.retryOn()) && tx.allowRetry(e)) {
      continue;                  // unbounded-looking loop; bounded by RetryController
    }
    if (throwing != e && instanceOf(e, spec.swallow())) {
      if (throwing != null) {
        throw throwing;          // swallow only hides COMMIT failures, never the cause
      }
      return result;
    }
  }
  if (throwing != null && throwing != e) {
    e.addSuppressed(throwing);
  }
  throw e;
}
```

**Flow:** begin → run body → classify the outcome: clean return or body-thrown exception ∈ `commitOn` ⇒ COMMIT then rethrow the body exception; anything else ⇒ ROLLBACK, then either retry (exception ∈ `retryOn` AND `tx.allowRetry` says yes), or swallow a distinct commit-phase exception (∈ `swallow`) while surfacing the ORIGINAL body exception, or propagate with the body exception attached as suppressed → finally: `tx.end()` (swallowed-and-traced). `instanceOf` checks cause chains one level deep, so wrapped persistence exceptions still match.
**Invariant:** the business exception is never lost — swallow applies only when `throwing != e` (i.e., the failure came from commit itself), and every non-swallowed path rethrows or suppress-preserves it. Retries are counted per-Transaction and gated by the shared `RetryController` (see `retry-controller-backoff`), not by this loop.
**Probe:** `nexus-transaction/src/test/java/org/sonatype/nexus/transaction/TransactionalTest.java` — `testCommitOnCheckedException` (:393), `testRollbackOnUncheckedException` (:376), `testRetrySuccessOnCheckedException` (:427), `testRetryFailureOnUncheckedException` (:503), `testRetrySuccessOnExceptionCause` (:527), `testRetryOnCommitFailure` (:587), `testSwallowCommitFailure` (:614), `testSwallowWontHideOriginalCause` (:636).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "TransactionalWrapper proceedWithTransaction commitOn retryOn swallow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exception-class-driven commit/retry/swallow matrix including the `throwing != e` swallow guard and suppressed-attachment. Adapt the AspectJ `ProceedingJoinPoint` carrier (any "run this lambda under tx" seam works — see `Operations.transactional`). Omit VM-error (`Throwable`) special-casing if your host has no equivalent. Eight-case test matrix verified on-disk at the pinned commit.
