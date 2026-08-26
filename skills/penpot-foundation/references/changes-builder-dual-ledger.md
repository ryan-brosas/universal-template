<!-- capsule-v2 -->
# Changes builder — how do you accumulate an edit that can both apply locally and undo exactly?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** How does a caller build one atomic edit (add/move/modify shapes) such that the same object carries its redo steps, its exact inverse undo steps, AND a live working copy of file-data to read old values from while building?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/files/changes_builder.cljc` : `empty-changes` / `with-objects` / `apply-changes-local` / `concat-changes` (:44-213).
**Signature:** `(empty-changes [origin page-id]) → changes` · `(with-objects changes objects) → changes'` · `(apply-changes-local changes & {:keys [apply-to-library?]}) → changes''`.
**Data Shape:** A changes value is a plain map `{redo-changes [] :vector, undo-changes '() :list, :origin …}`; everything else (page-id, the mounted file-data, applied-changes-count) lives in its **metadata**, not the map.

### Decisive source
```clojure
([] {:redo-changes []     ;; redo-changes is a vector so that conj adds things at the end, in order of execution
    :undo-changes '()})  ;; undo-changes is a list to conj things at the beginning, so they execute in the reverse order when undoing several changes
…
(defn apply-changes-local [changes & {:keys [apply-to-library?]}]
  (assert (check-changes changes) "expected valid changes")
  (if-let [file-data (::file-data (meta changes))]
    (let [index (::applied-changes-count (meta changes))
          new-changes (if (< index (count redo-changes)) (->> (subvec (:redo-changes changes) index) …) [])]
      … (vary-meta changes assoc ::file-data new-file-data ::applied-changes-count (count (:redo-changes changes))))
```

**Flow:** `with-page/with-container` mounts target id in meta → every builder fn (e.g. `add-object` :425-467) reads CURRENT objects via `(lookup-objects changes)` (= `::file-data` in meta) to capture old values into the undo entry, conj's redo onto the vector + inverse onto the list, then re-applies only the unapplied suffix (`subvec from ::applied-changes-count`) through `cfc/process-changes` so later builders see updated state → `concat-changes` merges two ledgers: vectors concat forward, lists concat REVERSED (`#(concat (:undo-changes changes2) %)`).
**Invariant:** undo entries must be captured from state BEFORE the redo applies (each builder reads then writes); `:undo-changes` is always a list so multi-change undo replays in reverse order without an explicit reverse step.
**Probe:** `grep -cF '(update :undo-changes #(concat (:undo-changes changes2) %))' common/src/app/common/files/changes_builder.cljc` → 1 (list-concat direction pins reverse-order undo).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "process-changes empty-changes with-objects changes_builder", limit: 10, fields: ["signature","name","file"] });
```
(verified live: `ext-penpot.common.src.app.common.files.changes_builder.*` resolves line-exact)

## Verdict
Adopt the dual-ledger shape (redo vector + undo list + metadata-mounted working state) for any collaborative-document editor port; adapt `uuid/zero` page-id aliasing used by `with-objects` (penpot test-harness detail); omit the plugin-data/library change variants (:270-325). Direct tests exist upstream (`files_builder_test.cljc`) but were not runnable in this environment — runner blocked honestly.
