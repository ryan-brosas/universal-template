<!-- capsule-v2 -->
# Shape-tree structure changes — how do add/move/delete keep parent-child invariants under component rules?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** What guards decide whether a shape may be reparented, and what does a delete cascade actually remove?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/files/changes.cljc` : `:mov-objects` handler `is-valid-move?`/`calculate-invalid-targets` (:735-765) + `common/src/app/common/files/helpers.cljc` : `delete-shape` (deletion ladder) + `changes_builder.cljc` `add-object` restore-touched undo entry (:449-467).
**Signature:** `(calculate-invalid-targets objects shape-id) → #{ids}` · `(is-valid-move? objects shape-id) → bool`.
**Data Shape:** shapes reference each other via `:parent-id`, `:frame-id`, and an ordered `:shapes` vector of child ids on the parent.

### Decisive source
```clojure
;; Avoid placing a shape as a direct or indirect child of itself, or
;; inside its main component if it's in a copy, or inside a copy, or from a copy
(is-valid-move? [objects shape-id]
  (let [invalid-targets (calculate-invalid-targets objects shape-id)
        shape (get objects shape-id)]
    (and shape
         (not (invalid-targets parent-id))                        ;; no self-nesting cycles
         (not (cfh/components-nesting-loop? objects shape-id parent-id))
         (or allow-altering-copies                                ;; explicit override
             (and (not (ctk/in-component-copy? (get objects (:parent-id shape))))
                  (not (ctk/in-component-copy? (get objects parent-id))))))))
```

**Flow:** move validation walks the candidate's whole descendant set (`calculate-invalid-targets` recurses through `:shapes`) so even indirect cycles are blocked → component-copy membership is checked on BOTH origin and target parents; only `allow-altering-copies` (component swap) or deprecated `syncing` bypass → deletion (`delete-shape`) collects ALL descendant ids first (`cfh/get-children-ids`), dissocs the whole subtree from `objects` in one reduce, then strips the id from the parent's ordered `:shapes` and clears `:remote-synced` on copy parents unless `ignore-touched` → `fix-broken-children` repairs dangling child refs by filtering `:shapes` against existing keys → builder side: `add-object` into a component-copy parent emits an EXTRA undo entry restoring the parent's `:touched` set, so undoing the add also un-marks the copy as locally-modified.
**Invariant:** the ordered `:shapes` vector is the render order AND z-index truth; every structural change must keep parent's `:shapes` consistent with children's `:parent-id` — deletes cascade the full subtree BEFORE touching the parent vector, or orphan ids linger.
**Probe:** `grep -cF 'd/update-when parent-id delete-from-parent' common/src/app/common/types/shape_tree.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "mov-objects delete-shape components-nesting-loop add-obj ignore-touched", limit: 10, fields: ["signature","name","file"] });
```
(verified live: resolves changes.cljc handlers line-exact; `files_builder_test.cljc` covers bool/media add flows)

## Verdict
Adopt descendant-set cycle blocking + dual-parent copy checks for any scene-graph with inheritance; adapt touched-restore semantics if you have no component copies; omit penpot-specific frame semantics. Coverage caveat: full mov-objects handler spans :735-860 — insert-position bookkeeping cited via files_builder tests, not exhaustively mined this pass.
