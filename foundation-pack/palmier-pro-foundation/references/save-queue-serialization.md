<!-- capsule-v2 -->
# Save-queue serialization — how do overlapping NSDocument saves serialize without writing a torn or stale snapshot?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** AppKit saves complete asynchronously — when a second save request arrives while the first write is still on disk, how do you guarantee exactly one snapshot is in flight and the *latest* document state wins?

## VideoProject.save / performNextSave FIFO queue
**Path/Symbol:** `Sources/PalmierPro/Project/VideoProject.swift:save` (136–147), `performNextSave` (149–164), `SaveRequest` (31–36).
**Signature:** `override func save(to url: URL, ofType typeName: String, for saveOperation: NSDocument.SaveOperationType, completionHandler: @escaping (Error?) -> Void)`.
**Data Shape:** `saveQueue: [SaveRequest]` where `SaveRequest = {url, typeName, operation, completion}`. One shared snapshot buffer (`snapshotProjectFile`, `snapshotManifest`, …) guarded by `snapshotPreparedForWrite`.

### Decisive source
```swift
editorViewModel.projectPackageCoordinator.saveStarted()
saveQueue.append(request)
guard saveQueue.count == 1 else { return }   // only the head drives AppKit
performNextSave()
// performNextSave:
captureSaveSnapshot()                        // snapshot captured at DEQUEUE time
super.save(to: request.url, ...) { error in
    coordinator.saveFinished(success: error == nil)
    request.completion(error)
    self.saveQueue.removeFirst()
    self.performNextSave()                   // drain chain
}
```

**Flow:** every `save` enqueues + counts in the coordinator → only the queue head calls `super.save` → AppKit eventually calls `write()` off-main against the snapshot captured when that request became head → completion pops the head and starts the next → each new head re-captures the snapshot, so state edited after an earlier request was enqueued is written by the later request.
**Invariant:** never two concurrent `super.save` calls on one document; the bytes that land last are captured from document state no older than the second request's dequeue; completions fire in FIFO order.
**Probe:** `Tests/PalmierProTests/Project/VideoProjectWriteUnblockTests.swift:124-164` (`overlappingSavesPreserveLatestSnapshot`: first save parked inside a delayed `writeSafely` via semaphores, timeline renamed "First save" then "Second save", both saves report success, re-read package asserts `timelines.first?.name == "Second save"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "performNextSave saveQueue SaveRequest serialize", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: enqueue-and-guard-count shape for any async-completion save API; capture the payload at dequeue time, not enqueue time, so queued requests always write fresher-than-enqueue state. Adapt the snapshot struct fields to your document model; the coordinator pairing (`saveStarted`/`saveFinished`) lives in its own capsule. Omit AppKit/NSDocument specifics if your host has synchronous writes. Coverage: VideoProject.swift parse-partial at 47–55+696 only (field declarations, read directly this pass); test file partial at 20–22+37 (fixtures, read directly).
