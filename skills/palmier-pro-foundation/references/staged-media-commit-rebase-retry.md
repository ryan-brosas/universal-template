<!-- capsule-v2 -->
# Staged-media commit rebase retry — how does a media file land in the project package even while the project is being renamed mid-save?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** A staged media file must be installed into `<project>/media/`, but the project URL can be rebased (Save As / rename) between admission and commit — how do you commit to the right destination or retry cleanly?

## commitStagedProjectMedia envelope
**Path/Symbol:** `Sources/PalmierPro/Editor/ViewModel/EditorViewModel+MediaLibrary.swift:EditorViewModel.commitStagedProjectMedia` (131–174; parse-partial 162–170 — claims from directly retrieved source, not graph edges).
**Signature:** `func commitStagedProjectMedia(_ stagedURL: URL, filename: String, maxBytes: Int64? = nil, workAlreadyAdmitted: Bool = false) async throws -> URL`.
**Data Shape:** staged temp file → prepared sibling temp file → installed `media/<filename>` inside the package; returns final destination URL; `nil` from the mutation closure signals "project URL moved, retry".

### Decisive source
```swift
for _ in 0..<3 {
    guard let targetProjectURL = projectURL else { break }
    try Task.checkCancellation()
    let preparedURL = try await Task.detached(priority: .userInitiated) {
        try FileIO.prepareStagedFile(from: stagedURL, nextTo: targetProjectURL, maxBytes: maxBytes)
    }.value
    defer { try? FileManager.default.removeItem(at: preparedURL) }
    if !workAlreadyAdmitted { try projectPackageCoordinator.beginMutation() }
    defer { if !workAlreadyAdmitted { projectPackageCoordinator.endMutation() } }
    if let destination = try await projectPackageCoordinator.performMutation({ () -> URL? in
        guard self.projectURL?.standardizedFileURL == targetProjectURL.standardizedFileURL
        else { return nil }                                   // rebased under us → retry
        let destination = targetProjectURL
            .appendingPathComponent(Project.mediaDirectoryName, isDirectory: true)
            .appendingPathComponent(filename, isDirectory: false)
        try FileIO.installPreparedFile(from: preparedURL, to: destination)
        return destination
    }) { return destination }
}
throw CocoaError(.fileNoSuchFile)
```

**Flow:** no open project ⇒ fall back to a temp-dir move → otherwise loop ≤3×: prepare bytes off-main next to the *target* URL, admit a package mutation (unless the caller already holds one at close time), then inside the coordinator-serialized closure RE-CHECK that `projectURL` still standardizes to the target captured at loop top — a mismatch (Save As happened during the save queue drain) yields `nil`, the mutation ends, and the loop recaptures the new URL and retries.
**Invariant:** an installed media file's path always matches the `projectURL` that was current when its manifest metadata lands; a rebase never leaves media in the old package with metadata pointing at the new one; the deferred cleanup removes every prepared temp file on every exit path.
**Probe:** `Tests/PalmierProTests/Project/ProjectPackageCoordinatorTests.swift:60-80` (`queuedMediaCommitUsesRebasedProjectURL`: commit queued behind a save, `fileURL` reassigned Old→New before `saveFinished`, commit resolves to `New.palmier/media/new.mp4`); `:107-140` (`admittedMediaWorkCommitsBeforeCloseSave`: `workAlreadyAdmitted: true` commit + import complete inside `beginMutation`, then close-save persists manifest entry `media/rendered.mp4`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "commitStagedProjectMedia performMutation workAlreadyAdmitted prepareStagedFile", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: target-capture + inside-closure revalidation + bounded retry for any "install artifact into a movable container" flow; pair it with the package-mutation-coordinator capsule. Adapt the retry budget (3) and the fallback-to-temp behavior. Omit `workAlreadyAdmitted` only if your host has no close-time admission window. Coverage: EditorViewModel+MediaLibrary.swift is parse-partial at 162–170 which intersects this range — evidence taken from directly retrieved source text; both probe tests read directly.
