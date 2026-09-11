<!-- capsule-v2 -->
# Registry standardized-URL ledger — how does a recently-loaded project list apply mutations that raced its async disk load?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** A singleton registry loads its entries from disk asynchronously at init — what happens to a `register()`/`remove()` call that lands before the load finishes, and what is the identity key for projects?

## ProjectRegistry isLoading deferral + standardizedFileURL identity
**Path/Symbol:** `Sources/PalmierPro/Project/ProjectRegistry.swift:mutate` (107–114), `finishLoading` (116–127), `load` (94–101), `register` (51–60), `updateURL` (81–90).
**Signature:** `@MainActor final class ProjectRegistry`; `private func mutate(_ apply: @escaping (inout [ProjectEntry]) -> Void)`; actor `ProjectRegistryDisk` owns all FileManager I/O.
**Data Shape:** `[ProjectEntry]` where `ProjectEntry { id: UUID, url, createdDate, lastOpenedDate }`; `pendingMutations: [(inout [ProjectEntry]) -> Void]`; identity = `url.standardizedFileURL`.

### Decisive source
```swift
private func mutate(_ apply: @escaping (inout [ProjectEntry]) -> Void) {
    guard !isLoading else {
        pendingMutations.append(apply)   // early mutation: parked, not lost, not applied to stale data
        return
    }
    apply(&entries)
    save()
}

private func finishLoading(_ loaded: [ProjectEntry]) {
    entries = loaded                     // disk truth REPLACES memory…
    isLoading = false
    guard !pendingMutations.isEmpty else { return }
    let mutations = pendingMutations
    pendingMutations.removeAll()
    for mutation in mutations { mutation(&entries) }   // …then parked mutations replay on top
    save()                               // single write for the whole batch
}
```

**Flow:** singleton init kicks an async disk load with `isLoading = true` → any mutation arriving mid-load is captured as a closure → when the load completes, disk entries replace memory, every parked closure replays against the loaded array in arrival order, and exactly one atomic save persists the combined result → after loading, each mutation applies immediately and saves synchronously (`try? data.write(..., options: .atomic)`). All lookups/dedup/rename compare `standardizedFileURL`, so `/tmp/x.palmier` and `file:///tmp//x.palmier` are one project.
**Invariant:** a mutation issued before load completion is never silently dropped and never applied to pre-load data that the disk would then overwrite; the registry writes at most once per load-generation; rename (`updateURL`) preserves entry id and bumps `lastOpenedDate`.
**Probe:** `Tests/PalmierProTests/Media/ProjectRegistryTests.swift:31-53` (`registerDeduplicatesByStandardizedURL`, `registerTreatsPathsWithExtraSlashesAsTheSameProject`: two URL forms of one path ⇒ count stays 1), `:93-115` (`updateURLChangesURLAndBumpsLastOpenedDate` + ghost-source no-op), `:133-145` (`registryPersistsAcrossLoadCycles`: fresh instance reloads the prior instance's entry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "ProjectRegistry mutate finishLoading pendingMutations standardizedFileURL", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: park-mutations-during-load + replay-on-loaded-truth + single-batched-save for any lazily-loaded mutable ledger; standardized-path identity for filesystem-keyed records. Adapt the closure type to your mutation vocabulary (here free `(inout [Entry]) -> Void`). Omit the trash/delete actor if you have no Finder-style deletion flow. Coverage: ProjectRegistry.swift + ProjectRegistryTests.swift no_recorded_issue + metadata_match; both read directly this pass.
