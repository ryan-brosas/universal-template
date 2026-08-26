<!-- capsule-v2 -->
# Close-save drain — how do you guarantee the final save persists unedited-state changes and that a failed close-save refuses the close?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** On window close, how do you flush one final save even when the document isn't marked edited, wait out admitted media work, and correctly veto the AppKit close when that save throws?

## canClose override + saveBeforeClosing repeat loop
**Path/Symbol:** `Sources/PalmierPro/Project/VideoProject.swift:canClose` (166–187), `saveBeforeClosing` (189–213).
**Signature:** `@MainActor func saveBeforeClosing() async throws`; `override func canClose(withDelegate:shouldClose:contextInfo:)`.
**Data Shape:** `isSavingBeforeClose: Bool` latch; coordinator `beginClosing()`/`waitUntilIdle()`/`cancelClosing()` phases.

### Decisive source
```swift
@MainActor
func saveBeforeClosing() async throws {
    isSavingBeforeClose = true
    defer { isSavingBeforeClose = false }
    let coordinator = editorViewModel.projectPackageCoordinator
    await coordinator.beginClosing()                 // flips isClosing + waits for idle
    do {
        repeat {
            guard let url = fileURL else { throw CocoaError(.fileNoSuchFile) }
            try await withCheckedThrowingContinuation { continuation in
                save(to: url, ofType: Self.typeIdentifier, for: .saveOperation) { error in
                    continuation.resume(with: error.map { .failure($0) ?? .success(()) }!)
                }
            }
        } while hasUnautosavedChanges                // at least ONE save, more if edits race in
        await coordinator.waitUntilIdle()
    } catch {
        coordinator.cancelClosing()                  // reopen the mutation gate on failure
        throw error
    }
}
```
and the close veto:
```swift
} catch {
    presentError(error)
    let callback = unsafeBitCast(target.method(for: shouldCloseSelector),
                                 to: DocumentCloseCallback.self)
    callback(target, shouldCloseSelector, self, false, contextInfo)   // shouldClose = false
}
```

**Flow:** `canClose` hops into a Task → runs the drain → only then forwards to `super.canClose`. The drain: begin closing (blocks NEW mutations), save once unconditionally (`repeat` runs even when `isDocumentEdited == false`, because snapshot capture can still differ from disk — e.g. a prior save snapshotted older state), loop while AppKit still reports unautosaved changes, wait for admitted media work to commit, and on any error cancel the closing gate and resume AppKit's delegate selector with `false` so the document stays open.
**Invariant:** a successful close implies every queued/admitted package mutation committed AND ≥1 final save returned success after it; a failed close-save never closes the window and re-enables mutations.
**Probe:** `Tests/PalmierProTests/Project/ProjectPackageCoordinatorTests.swift:82-105` (`nativeCloseWaitsForAcceptedMutationAndRejectsLateWork`: `probe.result == nil` while an admitted mutation is open, `true` only after `endMutation`, late `beginMutation` then throws CancellationError); `Tests/PalmierProTests/Project/ProjectClosePersistenceTests.swift:8-30` (`finalSavePersistsSnapshotWhenDocumentIsNotMarkedEdited`: clip duration mutated without `updateChangeCount`, `!document.isDocumentEdited` asserted, close-save still persists 90 frames).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "saveBeforeClosing canClose hasUnautosavedChanges waitUntilIdle", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: unconditional-at-least-one final save + dirty-loop + idle-wait before forwarding any "should close" decision; veto via the host's own callback protocol rather than exceptions. Adapt the delegate-callback mechanics (here raw `unsafeBitCast` of the ObjC selector) to your UI framework. Omit `isSavingBeforeClose` consumers if nothing else polls close state. Coverage: both probe tests read directly; VideoProject.swift ranges read whole-file.
