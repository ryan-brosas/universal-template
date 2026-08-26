<!-- capsule-v2 -->
# update-objects-tree traversal protocol — how do you walk every shape of a page AND every component with one function?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What is the single traversal contract that migrations, repair fixers, and bulk shape edits all plug into?

## Result-triple DFS over containers
**Path/Symbol:** `common/src/app/common/types/file.cljc` (`update-objects-tree` :266-307, `update-containers` :259-264, `update-all-shapes` :309-316).
**Signature:** `(update-all-shapes file-data f) -> file-data'` where `f : shape -> {:result :keep|:update|:remove, :updated-shape (when :update)}`.
**Data Shape:** file-data carries `:pages-index {page-id page}` and `:components {comp-id comp}` ("containers"). A container has `:objects {shape-id shape}` plus an ordered id vector (`:shapes` on pages via root; components use `:main-instance-id`). Each visited shape is wrapped `(with-meta shape {:container container})` so `f` can read its parent context via `(meta shape)`.

### Decisive source
```clojure
(let [root-id (if (ctn/page? container)
                uuid/zero
                (:main-instance-id container))]
  (if-not (empty? (:objects container))
    (update-shape-recursive container root-id)
    container))
;; ...inside update-shape-recursive:
(case result
  :keep    container
  :update  (ctst/set-shape container updated-shape)
  :remove  (ctst/delete-shape container shape-id true)
  ;; else: throw ex-info "Invalid result from update function"
  )
(if (= result :remove)
  container'
  (reduce update-shape-recursive container' (:shapes shape))))
```

**Flow:** for EACH container (page then component): pick root (`uuid/zero` for pages, `:main-instance-id` for component copies) → depth-first over the children id vectors → apply `f` at each node → dispatch on `:result`; after `:remove` recursion STOPS for that subtree (children are gone with it). Empty `:objects` short-circuits to the untouched container.
**Invariant:** The visitor contract is TOTAL — returning anything but the three keywords throws. Deletion is delegated to the tree primitive (`ctst/delete-shape … true`) instead of hand-editing maps, so index/vector consistency is maintained by one implementation; callers like `fix-missing-swap-slots` rely on `(meta shape)` for the container without re-deriving it.
**Probe:** deterministic greps from repo root: `grep -n 'uuid/zero' common/src/app/common/types/file.cljc` → :302 (the page root selection inside update-objects-tree) and :1044 (`:or {root-id uuid/zero}` default in a later helper — only :302 belongs to this seam); direct test evidence for consumers lives in the migration suite (`files_migrations_test.cljc` exercises this protocol indirectly through 0024b).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"update-all-shapes","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the result-triple visitor + with-meta container context + single-root-per-container DFS as a portable scene-graph editing kernel. Adapt root selection and delete semantics to your tree store. Omit Penpot's specific page/component duality if your document model lacks component copies.
