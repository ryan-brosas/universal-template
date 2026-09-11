<!-- capsule-v2 -->
# Lazy bounds propagation — how do group bounds see their children's NEW geometry while the new map is still being built?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** When a modifier moves a leaf, how does an entire ancestor chain of groups get recomputed bounds WITHOUT eager recursion and without derefing stale entries?

## Delay-per-entry + volatile holding the NEW map
**Path/Symbol:** `common/src/app/common/geom/bounds_map.cljc` (`objects->bounds-map` :19-23, `transform-bounds-map` :90-118, `resolve-modif-tree-ids` :59-88); `common/src/app/common/data.cljc:lazy-map` (:1018-1025).
**Signature:** `(objects->bounds-map objects)` → `{id (delay points4)}` ; `(transform-bounds-map bounds-map objects modif-tree)` / `(… ids)` → new `{id (delay bounds)}`.
**Data Shape:** values are 4-point vectors (`[p0 p1 p2 p3]`), never realized during construction; modif-tree is `{id {:modifiers …}}`; optional explicit `ids` set overrides ancestor resolution.

### Decisive source
```clojure
(let [bm-holder (volatile! nil)
      ids (or ids (resolve-modif-tree-ids objects modif-tree))
      new-bounds-map
      (loop [tr-bounds-map (transient bounds-map)
             ids (seq ids)]
        (if (not ids)
          (persistent! tr-bounds-map)
          (let [shape-id (first ids)]
            (recur
             (cond-> tr-bounds-map
               (not= uuid/zero shape-id)
               (assoc! shape-id
                       (delay (create-bounds (get objects shape-id)
                                             @bm-holder      ;; <-- THE NEW MAP
                                             objects
                                             modif-tree
                                             (get bounds-map shape-id)))))
             (next ids)))))
      ]
  (vreset! bm-holder new-bounds-map)   ;; only AFTER persistent!
  new-bounds-map)
```

**Flow:** widen modified ids upward through group-like ancestors (`get-parent-ids-seq` + `take-while group-like?`; CLJS twin uses mutable `js/Set` for perf) → transient-copy the old map, replacing ONLY widened ids with fresh delays that capture `@bm-holder` (the volatile) → `persistent!` → `vreset!` → later, when ANYONE derefs an entry, `create-bounds` resolves children through `@bm-holder` — i.e. the NEW map — so group bounds merge their children's modifier-transformed geometry.
**Invariant:** (1) The delays must close over the VOLATILE, not the map value — at assoc! time `new-bounds-map` doesn't exist yet; indirection through the late-`vreset!` volatile is the whole trick. Nothing can deref mid-construction because the map is unreachable before `vreset!`. (2) The last `create-bounds` arg is the OLD map entry (`current-ref`) — used to break self-reference loops (source comment: "fix a possible infinite loop with self-references"). (3) `uuid/zero` keys are never re-associated (root frame guard). (4) Unmodified shapes keep the ORIGINAL delay objects by reference — test pins id2's bounds are identical (`=`) pre/post. (5) Laziness is observable semantics: `objects->bounds-map` entries are `not (realized?)` until deref (test-pinned); `d/lazy-map` = `(into {} (map [k (delay (gen k))]) keys)`.
**Probe:** `common/test/common_tests/geom_bounds_map_test.cljc`: `objects->bounds-map-laziness-test` (delay realization order), `transform-bounds-map-move-in-group-test` (child move (50,50) → child origin (60,60) AND group entry present), `transform-bounds-map-explicit-ids-test` (explicit `#{id1}` leaves id2's entry identity-equal), `transform-bounds-map-deep-nesting-test` (leaf→grp1→grp2→grp3 all recomputed). Runner block: no clojure CLI in this environment — tests read directly, not executed.
**Retrieve (live-resolved rank#1–#4):**
```
search_graph {project:"penpot", query:"transform-bounds-map volatile delay bounds", limit:5}
→ rank1 transform-bounds-map :90-118 · #2 bounds-map :121-133 · #3 objects->bounds-map :19-23 · #4 create-bounds :25-57
```

## Verdict
Adopt the volatile-indirected lazy rebuild — it generalizes to any "derived map over a dependency graph" port. Adapt reader conditionals away if single-runtime. Omit the CLJS js/Set perf twin unless you have the same hot path. Graph caveat: inbound CALLS edges are unresolved for this symbol (callers_total=0); consumers confirmed from source at `modifiers.cljc:81,120,306,356-381`.
