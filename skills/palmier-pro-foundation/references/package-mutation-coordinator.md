<!-- capsule-v2 -->
# Package mutation coordinator — how do side-effecting media commits wait for in-flight saves without deadlocking or corrupting the package?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** A media import wants to write into the project package while a save is mid-flight — how do you admit it after the save settles, and what happens to queued work when that save FAILS?

## ProjectPackageCoordinator counters + queued-mutation commit/cancel
**Path/Symbol:** `Sources/PalmierPro/Project/ProjectPackageCoordinator.swift` (whole file, 87 L): `saveStarted` (12), `saveFinished(success:)` (14–29), `performMutation` (46–61), `beginClosing`/`waitUntilIdle` (63–73), `cancelMutation(id:)` (75–79).
**Signature:** `func performMutation<T: Sendable>(_ operation: @escaping () throws -> T) async throws -> T`; `@MainActor final class ProjectPackageCoordinator`.
**Data Shape:** `savesInProgress: Int`, `activeMutations: Int`, `pendingMutations: [(id: Int, run: () -> Void, cancel: () -> Void)]`, `idleWaiters: [CheckedContinuation<Void, Never>]`, `isClosing: Bool`.

### Decisive source
```swift
func saveFinished(success: Bool) {
    guard savesInProgress > 0 else { assertionFailure("Unbalanced project save completion"); return }
    savesInProgress -= 1
    guard savesInProgress == 0 else { return }
    let mutations = pendingMutations
    pendingMutations.removeAll()
    if !success { mutations.forEach { $0.cancel() } }   // failed save ⇒ queued work cancelled…
    else        { mutations.forEach { $0.run() } }      // …successful ⇒ committed in FIFO order
    resumeIdleWaitersIfNeeded()
}

func performMutation<T: Sendable>(_ operation: @escaping () throws -> T) async throws -> T {
    try Task.checkCancellation()
    guard savesInProgress > 0 else { return try operation() }   // fast path: nothing in flight
    let id = nextMutationID; nextMutationID += 1
    return try await withTaskCancellationHandler {
        try await withCheckedThrowingContinuation { continuation in
            pendingMutations.append((id: id,
                run:    { continuation.resume(with: Result { try operation() }) },
                cancel: { continuation.resume(throwing: CancellationError()) }))
        }
    } onCancel: { Task { @MainActor [weak self] in self?.cancelMutation(id: id) } }
}
```

**Flow:** every document save increments `savesInProgress` (`saveStarted` is called from `VideoProject.save` before enqueueing) → a mutation arriving while any save is outstanding parks its closure as a pending entry keyed by monotonically increasing id → when the LAST in-flight save finishes, queued closures run in order on success or are all cancelled with `CancellationError` on failure — the closing gate (`isClosing`) is never reopened by a failure → task cancellation removes just that entry by id → `waitUntilIdle()` suspends on a continuation until both counters hit zero.
**Invariant:** package writes never interleave with a save's snapshot→write window; queued work sees an all-or-nothing outcome of the preceding save generation; balanced counting is assertion-enforced; idle waiters wake exactly at the zero boundary.
**Probe:** `Tests/PalmierProTests/Project/ProjectPackageCoordinatorTests.swift:17-35` (`queuedMutationRunsBeforeSaveCompletionReturns`: two `saveStarted`, mutation observed parked, first `saveFinished(success:false)` keeps it parked, second success runs it), `:37-58` (`failedPreexistingSaveCancelsQueueWithoutReopening`: failure cancels the queued mutation AND leaves `beginMutation` throwing while closing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "performMutation beginMutation waitUntilIdle pendingMutations", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the two-counter + queued-closure shape whenever async whole-artifact publishes must exclude concurrent incremental writers; run-vs-cancel-on-last-completion is the load-bearing decision — a naive "wait for save then proceed" would commit media work into a half-written package. Adapt the cancellation plumbing to your structured-concurrency runtime. Omit `isClosing` if you have no close-time drain phase (PalmierPro pairs it with close-save-drain). Coverage: coordinator file no_recorded_issue + metadata_match; both probe tests read directly.
