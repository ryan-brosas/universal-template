<!-- capsule-v2 -->
# Package layout atomic writes — how is a document package (directory bundle) written so a crash mid-save never yields a half-updated project?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** A "document" is actually a directory of independent files (timeline.json, media.json, thumbnail, chat sessions, media/) — what write order and replacement rules keep the package internally consistent across saves and Save As?

## writeProjectPackage file ladder
**Path/Symbol:** `Sources/PalmierPro/Project/VideoProject.swift:writeProjectPackage` (303–323), `createPackageDirectory` (325–332), `writeChatDirectory` (334–343), `copyPreservedFile` (345–354), `copyMediaDirectoryIfNeeded` (356–365).
**Signature:** `nonisolated static func writeProjectPackage(_ snapshot: ProjectPackageSnapshot, to packageURL: URL, sourceURL: URL?) throws`.
**Data Shape:** `ProjectPackageSnapshot { timeline: Data, manifest: Data?, thumbnail: Data?, chatSessionFiles: [(name, data)] }`; per-file `.atomic` writes; `sourceURL` nil-able and compared via standardized paths.

### Decisive source
```swift
try createPackageDirectory(at: packageURL, fm: fm)          // remove file-at-path blocker, mkdir -p
try snapshot.timeline.write(to: ...timelineFilename, options: .atomic)
if let manifest = snapshot.manifest {
    try manifest.write(to: ..., options: .atomic)
} else { try copyPreservedFile(Project.manifestFilename, from: sourceURL, to: packageURL, fm: fm) }
if let thumbnail = snapshot.thumbnail { ... .atomic }
else { try copyPreservedFile(Project.thumbnailFilename, ...) }
try writeChatDirectory(snapshot.chatSessionFiles, to: packageURL, fm: fm)   // rm -rf + rewrite
try copyMediaDirectoryIfNeeded(from: sourceURL, to: packageURL, fm: fm)     // only when source != dest
try fm.createDirectory(at: ...mediaDirectoryName, withIntermediateDirectories: true) // always exists
```

**Flow:** timeline data first (the primary document — its presence defines a readable package) → manifest and thumbnail written when new bytes exist, else preserved-copied from the source package → chat directory replaced wholesale (delete + recreate + atomic per-file writes) → on Save As (`sourceURL != packageURL`) the whole `media/` directory is copied so references survive the move → finally the empty `media/` directory is guaranteed to exist even for brand-new projects.
**Invariant:** every individual file write is atomic; a failed save can leave a stale-but-consistent package (old files intact) rather than truncated ones; Save As destinations are self-contained copies; same-file in-place autosave never re-copies media over itself (`sameFile` guard).
**Probe:** `Tests/PalmierProTests/Project/VideoProjectLoadTests.swift:264-280` (`packageWriteCreatesMediaDirectory`: even an all-nil-snapshot write materializes `media/`), `:282-304` + `:306-325` (manifest preservation twins, byte-equality assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "writeProjectPackage createPackageDirectory copyMediaDirectoryIfNeeded chat directory", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: primary-document-first ordering + per-file atomicity + preserve-or-write sidecar rule + copy-on-relocate for directory-bundle documents. Adapt which file is "primary" and whether wholesale directory replacement is acceptable for your payload sizes. Omit the media-directory copy if artifacts are content-addressed outside the package. Coverage: VideoProject.swift parse-partial ranges read directly; all three probe tests read directly.
