<!-- capsule-v2 -->
# Modif-tree persistence & structure application — where do uncommitted changes live, and how do structural edits reach descendants?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How do you hold per-shape in-flight modifiers across UI updates without touching the document — and how does one shape's structural change cascade to its children?

## Dissoc-on-empty id→modifiers map + structure-only descendant fan-out
**Path/Symbol:** `common/src/app/common/geom/modif_tree.cljc` (`add-modifiers` :13-27, `merge-modif-tree` :29-36, `apply-structure-modifiers` :38-55); combinator `ctm/add-modifiers` at types/modifiers.cljc:380-405.
**Signature:** `(add-modifiers modif-tree id modifiers)` → tree' ; `(merge-modif-tree t1 t2)` → merged ; `(apply-structure-modifiers objects modif-tree)` → objects'.
**Data Shape:** `{shape-id {:modifiers Modifiers}}` — plain map, no wrapper record; empty modifiers NEVER stored.

### Decisive source
```clojure
(defn add-modifiers
  [modif-tree id modifiers]
  (if (ctm/empty? modifiers)
    modif-tree
    (let [old-modifiers (dm/get-in modif-tree [id :modifiers])
          new-modifiers (ctm/add-modifiers old-modifiers modifiers)]
      (cond-> modif-tree
        (ctm/empty? new-modifiers)   ;; cancellation leaves NO residue
        (dissoc id)

        (not (ctm/empty? new-modifiers))
        (assoc-in [id :modifiers] new-modifiers)))))
```

**Flow:** every interactive update re-enters through `add-modifiers`, which MERGES into the existing entry via the ordered-op combinator; when ops cancel (e.g. drag back to start merges vectors to zero → resize/move optimized away), the entry is dissoc'd so "no live modification" stays representable as absence. On commit, geometry modifiers are applied per-shape and dropped. Structure ops take a separate path: `apply-structure-modifiers` walks ONLY entries with `has-structure?`, applies them to the target, and if the entry ALSO has structure-CHILD ops, projects them via `select-child-structre-modifiers` onto ALL descendant ids.
**Invariant:** (1) Absence-is-empty semantics: code must treat missing key and empty-modifiers identically; storing empties breaks the dissoc-on-cancel contract (grep pin: `(dissoc id)` exactly once). (2) Structure fan-out uses the PROJECTION (`select-child-structre-modifiers` keeps only structure-child), so children receive scale-content/rotation-field deltas but NOT the parent's move/resize/add-children — porting the full modifier set down double-applies geometry. (3) Merge order matters across trees: `merge-modif-tree` reduces `add-modifiers` so overlapping ids compose by op order, not last-write-wins.
**Probe:** `common/test/common_tests/geom_modif_tree_test.cljc` — 3 deftests whole-file (:15-77): empty-add no-ops AND keeps unrelated ids; non-empty creates entry; same-id add MERGES; merge of disjoint trees keeps both, overlapping ids merge, merging {} returns original. Census pins: `grep -c '(t/deftest' common/test/common_tests/geom_modif_tree_test.cljc` → 3 ; `grep -cF '(dissoc id)' common/src/app/common/geom/modif_tree.cljc` → 1 ; `grep -cF 'select-child-structre-modifiers' geom/modif_tree.cljc` → 1.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"add-modifiers merge modif-tree structure","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the dissoc-on-empty persistence rule and the projected structure-child fan-out. Adapt entry payload shape (`{:modifiers …}` wrapper) to your state store. Omit nothing else — the file is 55 lines and fully owned by this capsule.
