<!-- capsule-v2 -->
# Marker category migration plane — how do you migrate secondary-model items when their type registry changes, as one undoable entry, without a per-item undo storm?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** when a user deletes or remaps marker categories (a global registry), every marker of an affected type must change or vanish — how does kdenlive fold that fan-out into ONE undo entry while keeping the snap grid exact?

## Category registry + marker migration seam
**Path/Symbol:** `src/bin/model/markerlistmodel.cpp:loadCategoriesWithUndo` (:52-78) + `loadCategories` (:80-103) + `categoriesToStringList` (:105-115); registry `src/core.h:MarkerCategory` struct (:355) + `pCore->markerTypes` QMap (:360); production caller `src/doc/kdenlivedoc.cpp:429`.
**Signature:** `void loadCategoriesWithUndo(const QStringList &categories, const QStringList &currentCategories, const QMap<int, int> remapCategories = {})`; `QList<int> loadCategories(const QStringList &categories, bool notify = true)`.
**Data Shape:** category string format `"displayName:ix:color"` (name may contain colons — parsed with `section(QLatin1Char(':'), 0, -3)`); `pCore->markerTypes` is a global `QMap<int, MarkerCategory{color, displayName}>`; `remapCategories` maps deleted category ix → surviving category ix; `loadCategories` returns `previousCategories` (the ixs present before, minus still-present ones) as the deletion diff.

### Decisive source
```cpp
// markerlistmodel.cpp:52-78 — the whole migration on private accumulators
void MarkerListModel::loadCategoriesWithUndo(const QStringList &categories, const QStringList &currentCategories, const QMap<int, int> remapCategories)
{
    // Remove all markers of deleted category
    Fun local_undo = []() { return true; };
    Fun local_redo = []() { return true; };
    QList<int> deletedCategories = loadCategories(categories);
    while (!deletedCategories.isEmpty()) {
        int ix = deletedCategories.takeFirst();
        const QList<CommentedTime> toDelete = getAllMarkers(ix);
        if (remapCategories.contains(ix)) {
            int newType = remapCategories.value(ix);
            for (const auto &c : toDelete) {
                addMarker(c.time(), c.comment(), newType, local_undo, local_redo);
            }
        } else {
            for (const auto &c : toDelete) {
                removeMarker(c.time(), local_undo, local_redo);
            }
        }
    }
    Fun undo = [this, currentCategories]() { loadCategories(currentCategories); return true; };
    Fun redo = [this, categories]() { loadCategories(categories); return true; };
    PUSH_FRONT_LAMBDA(local_redo, redo);
    PUSH_LAMBDA(local_undo, undo);
    pCore->pushUndo(undo, redo, i18n("Update timeline markers categories"));
}
```

**Flow:** (1) `loadCategories(categories)` swaps the global registry in place, skipping malformed strings (fewer than two `:` separators), and returns the ixs that disappeared; (2) for each deleted category, its markers are enumerated (`getAllMarkers(ix)`) and either re-added with the remapped type or removed — each via the ordinary `addMarker`/`removeMarker` entry points composed onto PRIVATE `local_undo`/`local_redo` accumulators, so every per-marker snap-point bookkeeping (start + range end) still runs exactly as in interactive edits; (3) the registry swap itself is wrapped as outer undo/redo lambdas (re-calling `loadCategories` with the old/new lists); (4) `PUSH_FRONT_LAMBDA(local_redo, redo)` + `PUSH_LAMBDA(local_undo, undo)` compose the registry swap AROUND the marker migration (undo: restore registry first, then un-migrate markers; redo: re-apply registry, then re-migrate), and ONE `pCore->pushUndo` entry lands on the stack; (5) `loadCategories(notify=true)` emits `dataChanged` for the ColorRole refresh and `pCore->saveGuideCategories()` for document persistence.

**Invariant:** the per-marker mutation path is NEVER bypassed — migration reuses `addMarker`/`removeMarker` with private accumulators rather than touching `m_markerList` directly, so snap grids, undo composition, and the id counter stay exact; the registry restore is ordered OUTSIDE the marker migration in both directions (registry first on undo, registry first on redo) because marker types are validated against the live registry. The round-trip format `categoriesToStringList()` (`"name:ix:color"`) is the same parser `loadCategories` consumes, so preferences storage needs no separate codec.

**Probe:** `tests/markertest.cpp:170-206` "Test Categories" SECTION (read directly, whole): 9 default categories asserted; `newCategories.removeFirst()` then `loadCategoriesWithUndo(newCategories, categories)` drops the deleted category's marker (rowCount 2→1) while the snap mirror stays exact (`rowCount == snaps->_snaps().size()` asserted at every step); `undoStack->undo()` restores rowCount 2. Executed deterministic probe:
```
grep -rn "loadCategoriesWithUndo" src/ tests/
```
→ markerlistmodel.hpp:176 (declaration), markerlistmodel.cpp:52 (definition), kdenlivedoc.cpp:429 (production caller), markertest.cpp:195 (only test) — 4 hits, quoted from the run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "loadCategoriesWithUndo remapCategories marker category migration", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph MCP was not connected in the authoring session; the grep probe above was executed byte-for-byte instead.)

## Verdict
Adopt the reuse-don't-bypass pattern: registry fan-out migrations compose the per-item ordinary mutators onto private accumulators, then fold into one stack entry with the registry swap ordered outside the item migration; adopt the diff-returning registry swap (`previousCategories`) so the caller never recomputes what changed. Adapt the string-serialized registry format and the global pCore singleton to your host's settings store. Omit the KDE i18n and the ColorRole dataChanged plumbing. State the caveat: exactly one test covers this plane (markertest.cpp "Test Categories"); the remapCategories branch (ix → new ix) has no test coverage — verify it in your port.
