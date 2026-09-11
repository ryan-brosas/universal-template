<!-- capsule-v2 -->
# Convenience modifier builders — how are rotation-about-foreign-center and orientation swaps compiled into primitive ops?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How does "rotate this shape 90° around the selection's center" become move+rotation operations, and how do width/height/proportion/lock rules turn into a single resize?

## Derived-op builders over the primitive vocabulary
**Path/Symbol:** `common/src/app/common/types/modifiers.cljc` (`rotation-modifiers` :424-437, `change-size` :444-452, `change-dimensions-modifiers` :454-486, `change-orientation-modifiers` :488-512).
**Signature:** `(rotation-modifiers shape center angle)` → Modifiers ; `(change-size shape width height)` → Modifiers ; `(change-dimensions-modifiers shape attr value opts)` → Modifiers ; `(change-orientation-modifiers shape orientation)` → Modifiers.
**Data Shape:** reads shape `:points :transform :transform-inverse :proportion :proportion-lock` and safe-size dims; produces standard GeometricOperation logs (see four-bucket capsule).

### Decisive source
```clojure
(defn rotation-modifiers
  [shape center angle]
  (let [shape-center (gco/shape->center shape)
        ;; Translation caused by the rotation
        move-vec
        (gpt/transform
         (gpt/point 0 0)
         (-> (gmt/matrix)
             (gmt/rotate angle center)          ;; rotate origin point about FOREIGN center
             (gmt/rotate (- angle) shape-center)))] ;; ...then UNDO about own center
    (-> (empty)
        (rotation shape-center angle)
        (move move-vec))))
```

**Flow:** rotating about a center ≠ the shape's own center displaces it; the builder computes that displacement as the image of the origin under (rotate-about-foreign ∘ unrotate-about-self), then emits geometric-rotation + compensating-move. Dimension changes: clamp requested value to ≥0.01 (`(< (abs value) 0.01) → 0.01`, comment "Avoid having shapes with zero size"), honor `:proportion-lock` by deriving the sibling axis via `:proportion` unless `{:ignore-lock? true}`, and emit resize with scale = requested/safe-current. Orientation swap picks max/min of w/h per target orientation and scales from the TRANSFORMED top-left corner (origin pre-mapped through `:transform` when present).
**Invariant:** (1) The rotation compensation pair must stay exact inverses — porting only the forward rotation moves shapes whose user intent was spin-in-place. Direct test: `rotation-modifiers returns move + rotation in geometry-child` (modifiers_test :395-400). (2) The 0.01 floor is applied to the REQUESTED value before ratio math (test pins scale 0.0001 for request 0.001 on a 100-wide shape :151-157). (3) Proportion lock derives the OTHER axis — locking width drives height by ÷proportion, height drives width by ×proportion (:470-476), each covered by its own deftest. (4) Degenerate selrects must not throw: three dedicated deftests assert `some? mods` for zero-width/zero-height/both (:663-691).
**Probe:** direct tests all in `common/test/common_tests/types/modifiers_test.cljc`: `change-size-basic` :57-98 (incl nil-axis fallbacks + identity-optimized-away), `change-dimensions-modifiers-with-proportion-lock` :124-149, `-value-clamping` :151-164, `-end-to-end` :166-179 (real selrect after transform-shape), `change-orientation-zero-*-selrect-does-not-throw` :675-691. Census pin: `grep -cF '(safe-size-rect shape)' common/src/app/common/types/modifiers.cljc` → 4.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"safe-size-rect fallback empty-rect","limit":5,"detail":"ids"}'
```
(same builders plane; route by Source line.)

## Verdict
Adopt the foreign-center rotation compensation and the clamp→lock→ratio pipeline. Adapt proportion/orientation semantics to your property model. Omit text-content scaling inside scale-content ops (Penpot text model).
