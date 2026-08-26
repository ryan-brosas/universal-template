<!-- capsule-v2 -->
# Async-write main-thread unblock — how does an off-main document write avoid deadlocking the AppKit main thread?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** With `canAsynchronouslyWrite == true`, AppKit parks the main thread until `write()` calls `unblockUserInteraction()` — how do you guarantee that call happens exactly once even when `write()` throws early?

## writeSafely / write unblock discipline
**Path/Symbol:** `Sources/PalmierPro/Project/VideoProject.swift:writeSafely` (215–223), `write` (225–267).
**Signature:** `override func write(to url: URL, ofType typeName: String) throws`; `override func canAsynchronouslyWrite(to:ofType:for:) -> Bool { true }`.
**Data Shape:** snapshot buffer + `snapshotPreparedForWrite: Bool`; a local `mainThreadUnblocked` flag paired with `defer`.

### Decisive source
```swift
override func writeSafely(to url: URL, ofType typeName: String, for saveOperation: ...) throws {
    // NSDocument otherwise blocks the main thread while super prepares a safe-save directory.
    unblockUserInteraction()
    try super.writeSafely(to: url, ofType: typeName, for: saveOperation)
}

override func write(to url: URL, ofType typeName: String) throws {
    var mainThreadUnblocked = false
    defer { if !mainThreadUnblocked { unblockUserInteraction() } }   // exactly-once on ANY exit

    if !snapshotPreparedForWrite {
        guard Thread.isMainThread else {
            Log.project.error("save: snapshot not prepared for off-main write()")
            throw CocoaError(.fileWriteUnknown)   // throws AFTER defer registered → still unblocks
        }
        MainActor.assumeIsolated { captureSaveSnapshot(); snapshotSourceProjectURL = fileURL }
    }
    ...
    unblockUserInteraction()
    mainThreadUnblocked = true
```

**Flow:** `canAsynchronouslyWrite=true` makes AppKit run encode+disk-write off-main while holding the main thread in `_waitForUserInteractionUnblocking` → `write()` must release it before doing slow work → both entry points unblock first, then work; the `defer` flag pattern makes the release idempotent across the throw path (missing snapshot off-main), the success path, and the `super.writeSafely` re-entry path.
**Invariant:** every path out of `write()`/`writeSafely()` calls `unblockUserInteraction()` at least once and never twice; an off-main `write()` without a prepared snapshot fails loudly (`fileWriteUnknown`) but still releases the main thread. Upstream pinned as issue #402 ("a throw that skips the unblock freezes the app permanently").
**Probe:** `Tests/PalmierProTests/Project/VideoProjectWriteUnblockTests.swift:72-86` (`offMainWriteWithoutSnapshotThrowsButStillUnblocks`: detached-task `write` throws CocoaError AND `unblockCount == 1`), `:88-102` (`successfulWriteUnblocksExactlyOnce`), `:104-122` (`safeWriteUnblocksBeforeEnteringWrite`: counting subclass records `unblockCountAtWriteEntry == 1`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "unblockUserInteraction writeSafely snapshotPreparedForWrite", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the defer-flagged single-release pattern for any host API that parks a thread until a callback fires — register the release before the first throw site. Adapt which thread "main" is and whether snapshots are captured lazily inside `write`. Omit `MainActor.assumeIsolated` gymnastics if your document model is already Sendable-clean. Coverage: VideoProject.swift parse-partial ranges read directly; all three probe tests read whole.
