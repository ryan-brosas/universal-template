<!-- capsule-v2 -->
# Modifiers record — how do you accumulate interactive drag operations so they can be applied, merged, and projected later?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What is the data structure that lets the editor apply "what the user is doing right now" to shapes without committing it to the document?

## Four-bucket operation log with global order
**Path/Symbol:** `common/src/app/common/types/modifiers.cljc` (`Modifiers` defrecord :46-51, `GeometricOperation` :53-61, `StructureOperation` :63-67, op constructors :71-108, builder API `move`/`resize`/`rotation`/`move-parent`/`resize-parent`/`remove-children`/`add-children`/`reflow`/`scale-content`/`change-property` :238-344).
**Signature:** `(ctm/empty)` → Modifiers ; `(move modifiers vector)` → modifiers' ; `(resize modifiers vector origin transform transform-inverse)` ; `(rotation modifiers center angle)` ; `(add-modifiers m1 m2)` → combined.
**Data Shape:** `Modifiers[last-order, geometry-parent, geometry-child, structure-parent, structure-child]`; geometry buckets hold `GeometricOperation[order type vector origin transform transform-inverse rotation center]`, structure buckets hold `StructureOperation[type property value index]`. Semantics per header comment :28-44: geometry-parent = NON-recursive geometry; geometry-child = recursive; structure-parent = non-recursive structural (add/remove children, reflow, change-property); structure-child = recursive structural (scale-content, rotation-as-field, change-properties).

### Decisive source
```clojure
(defrecord Modifiers
           [last-order ;; Last `order` attribute in the geometry list
            geometry-parent
            geometry-child
            structure-parent
            structure-child])
;; every builder: order = (inc last-order), then maybe-add-* merge-or-append
(defn move
  ([modifiers x y] ...)
  ([modifiers vector]
   ... (cond-> modifiers
         (move-vec? vector)
         (update :geometry-child maybe-add-move (move-op order vector)))))
```

**Flow:** UI interactions build modifiers via builders; each builder bumps `last-order` and appends into exactly ONE bucket — zero-vector moves and unit/identity resizes are optimized AWAY (`move-vec?`/`resize-vec?` gates), unless `{:keys [precise?]}` (:300-307). Two consecutive same-type ops at the head MERGE: moves sum vectors (:177-182), resizes multiply componentwise but ONLY if same origin AND close transforms (:155-175); a merged op that becomes negligible pops instead of pushing (:206-208/:222-224). Rotation is DUAL-BUCKET by design: one geometric rotation (with center) + one structural rotation that increments the shape's `:rotation` field (:309-317) — porters who implement only one arm get either moved-but-not-labeled or labeled-but-not-moved shapes.
**Invariant:** (1) `last-order` must stay monotone across merges — `modifiers->transform` sorts parent+child together by `order` (:646-652), so bucket placement never changes application sequence, only propagation scope. (2) The merge gates in `add-modifiers` are ASYMMETRIC: child ops only merge when BOTH sides have empty parent lists and vice versa (:398-399) — merging across scopes would silently reorder relative to foreign ops. (3) Builders are total over nil modifiers (`(or modifiers (empty))`) — chains compose without wrapping.
**Probe:** `common/test/common_tests/types/modifiers_test.cljc` — 31 deftests pin this plane whole: `move-builder` (:251-272: zero-vector optimized away; two moves merge to 15), `resize-builder` (:274-297 incl `precise?` keeps near-identity :284-287), `rotation-builder` (:299-310: dual-bucket + zero-angle no-op), `add-modifiers-combinator` (:404-428: disjoint moves sum; last-order sums), `predicate-only-move?` vacuously true on empty (:492-493). Census pins: `grep -c '(t/deftest' common/test/common_tests/types/modifiers_test.cljc` → 31 ; `grep -c 'move-vec?' common/src/app/common/types/modifiers.cljc` → 4 ; `grep -c 'resize-vec?' <same>` → 6.
**Retrieve (live-resolved):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"Modifiers record geometry parent child structure operations","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the four-bucket ordered-log design with head-merge semantics and dual-bucket rotation. Adapt the specific StructureOperation set (reflow/scale-content are Penpot-layout coupled) to your host's structural vocabulary. Omit the text-content scaling internals (`scale-text-content` :669-673) unless porting Penpot text nodes.
