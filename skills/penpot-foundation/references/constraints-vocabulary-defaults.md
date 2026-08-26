<!-- capsule-v2 -->
# Constraint vocabulary reduction — how do 8 stored constraints become 4 behaviors, and what happens when a shape has none?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** When porting parent-resize propagation, how do I model the constraint vocabulary so stored values, missing values, and tree position all behave correctly without persisting defaults?

## Path/Symbol
`common/src/app/common/geom/shapes/constraints.cljc` — `const->type+axis` :240–248, `default-constraints-h` :250–256, `default-constraints-v` :258–264; consumed by `calc-child-modifiers` :292–361.

**Signature:**
```clojure
(def const->type+axis {:left :start :top :start :right :end :bottom :end
                       :leftright :fixed :topbottom :fixed :center :center :scale :scale})
(defn default-constraints-h [shape] ...)   ;; nil | :left | :scale
(defn default-constraints-v [shape] ...)   ;; nil | :top  | :scale
```
**Data Shape:** shapes store `:constraints-h` / `:constraints-v` as one keyword each from the 8-value vocabulary. Defaults are FUNCTIONS OF TREE POSITION (`:parent-id`, `:frame-id`), never written back to the shape.

### Decisive source
```clojure
(defn default-constraints-h
  [shape]
  (if (= (:parent-id shape) uuid/zero)
    nil
    (if (= (:parent-id shape) (:frame-id shape))
      :left
      :scale)))
```
(constraints.cljc :250–256; `-v` is the same ladder returning `:top`.)

**Flow:** `calc-child-modifiers` reads `(:constraints-h child (default-constraints-h child))` — a lookup WITH computed fallback, so: root-level shapes (parent-id = uuid/zero) get `nil` → `const->type+axis` yields nil → `constraint-modifier` dispatches to `:default` → `[]` (no propagation at canvas root); direct children of their own frame pin to `:left`/`:top` (frame resize moves them, doesn't scale them); group children default to `:scale` (group resize scales content). The 8 stored keywords reduce onto exactly four multimethod types: `:start` (:left/:top), `:end` (:right/:bottom), `:fixed` (:leftright/:topbottom — BOTH edges pinned ⇒ grow), `:center`; `:scale` short-circuits earlier.

**Invariant:** (1) Defaults are derived per-call from tree position — never persisted, so re-parenting instantly changes behavior with no migration. (2) The three-way default ladder is ordered: root → nil beats frame-check; frame-child → :left/:top beats :scale. (3) `nil` constraint is safe end-to-end because `(nil const->type+axis)` misses and the `:default` multimethod method returns `[]` — arity-pinned by the ONLY direct test in the plane (`geom_shapes_constraints_test.cljc`: `:default` takes 6 positional args post-fix and returns `[]`). (4) `:scale + :scale` exits `calc-child-modifiers` before any geometry work (fast path).
**Probe:** `common/test/common_tests/geom_shapes_constraints_test.cljc` (read FULL, 27 lines): `constraint-modifier-default-returns-empty-vector` asserts `(gsc/constraint-modifier :unknown-constraint-type :x nil nil nil nil)` is an empty vector on both axes. No numeric test exists for the default ladders — source-only evidence (runner block: no clojure CLI in this environment; tests read, not executed).
**Retrieve (live-resolved rank#1/#2/#4):**
```
search_graph {project:"penpot", query:"default-constraints-h const->type+axis vocabulary", file_pattern:"*shapes/constraints*"}
→ rank1 const->type+axis :240-248 · #2 default-constraints-h :250-256 · #3 other-axis · #4 default-constraints-v :258-264
```

## Verdict
Adopt the lookup-with-computed-fallback idiom (`(:key shape (derive-default shape))`) and the N-stored→M-behavior reduction table for any constraint/attachment system. Adapt the vocabulary keywords to your domain but keep `fixed` meaning BOTH-edges-pinned (it implies growth, not immobility — see fixed-constraint-resize-sandwich.md). Omit nothing here; the module is small and total.
