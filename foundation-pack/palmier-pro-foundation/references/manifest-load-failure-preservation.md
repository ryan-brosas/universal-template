<!-- capsule-v2 -->
# Manifest load-failure preservation — how does a save avoid clobbering an unreadable sidecar file with an empty replacement?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** The document opens fine but a secondary file (media manifest) fails to decode — how do you degrade to "data offline" on read while guaranteeing no later save destroys the recoverable original bytes?

## manifestLoadFailed flag → snapshot suppression → preserved copy
**Path/Symbol:** `Sources/PalmierPro/Project/VideoProject.swift:readProjectPackage` (112–127), `manifestSnapshot` (282–286), `writeProjectPackage` (303–311), `copyPreservedFile` (345–354); flag at :47, cleared at :265–266.
**Signature:** `nonisolated static func manifestSnapshot(manifest: MediaManifest, loadFailed: Bool) -> MediaManifest?`; `nonisolated static func writeProjectPackage(_ snapshot: ProjectPackageSnapshot, to packageURL: URL, sourceURL: URL?) throws`.
**Data Shape:** `ProjectPackageContents { projectFile, manifest?, manifestUnreadable }` on read; `ProjectPackageSnapshot { timeline: Data, manifest: Data?, thumbnail: Data?, chatSessionFiles }` on write; `nil` snapshot manifest is the "nothing new to say" signal.

### Decisive source
```swift
// read: bad manifest must not lose the project
if let decoded = try? JSONDecoder().decode(MediaManifest.self, from: manifestData) {
    manifest = decoded; manifestUnreadable = false
} else {
    Log.project.error("read manifest decode failed ... opening with empty manifest")
    manifest = nil; manifestUnreadable = true
}

// write-side gate: don't overwrite the recoverable original with an empty one
static func manifestSnapshot(manifest: MediaManifest, loadFailed: Bool) -> MediaManifest? {
    if loadFailed && manifest.entries.isEmpty && manifest.folders.isEmpty { return nil }
    return manifest
}

// package writer: nil ⇒ carry the original bytes forward instead of writing nothing
if let manifest = snapshot.manifest {
    try manifest.write(to: packageURL.appendingPathComponent(Project.manifestFilename), options: .atomic)
} else {
    try copyPreservedFile(Project.manifestFilename, from: sourceURL, to: packageURL, fm: fm)
}
```

**Flow:** decode failure on open sets `manifestLoadFailed` and opens with an empty in-memory manifest → every save snapshots through `manifestSnapshot`, which suppresses the empty manifest to `nil` only while the failure flag is set AND the in-memory manifest is still empty (user re-added media ⇒ real data exists again) → the package writer copies the original file byte-for-byte from `sourceURL` (skipped when source==dest for the same-file in-place autosave) → after any real manifest is written, `write()` clears `manifestLoadFailed` (:265–266) so preservation ends exactly once.
**Invariant:** a corrupt-but-present sidecar survives every save untouched until the app has genuinely better bytes to replace it with; "empty because load failed" and "empty because user deleted everything" are distinguished states.
**Probe:** `Tests/PalmierProTests/Project/VideoProjectLoadTests.swift:282-304` (`saveAsPreservesUnreadableManifestFile`: sentinel bytes `"ORIGINAL-CORRUPT-MANIFEST-BYTES"` carried verbatim into the SaveAs destination), `:306-325` (`inPlaceSaveLeavesUnreadableManifestUntouched`: same-file autosave leaves originals byte-equal), `:264-280` (`packageWriteCreatesMediaDirectory`: media dir always materialized).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "manifestSnapshot copyPreservedFile manifestUnreadable", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the three-part contract — fail-open read flag, empty-means-lost suppression at snapshot time, byte-preserving copy at write time — for ANY secondary artifact saved beside a primary document. Adapt the emptiness test to your domain model. Omit thumbnail twin-handling if you have no binary sidecar (same pattern applies). Coverage: all cited paths checked this pass; VideoProjectLoadTests read directly.
