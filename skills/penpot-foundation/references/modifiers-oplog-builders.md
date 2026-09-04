<!-- capsule-v2 -->
# Modifiers builder — how do live drag operations compose into one ordered, mergeable transform?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** How does penpot accumulate a stream of pointer events (move/resize/rotate) into per-shape modifiers that stay cheap during the drag and apply exactly once at commit — without ever letting zero-ops or misordered ops corrupt geometry?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/types/modifiers.cljc` : `Modifiers` record + builder API (`move`/`resize`/`rotation`, :233-344) + merge machinery (`maybe-add-move/resize`, :198-225) + `add-modifiers` (:380-405).
**Signature:** `(move modifiers vector) → modifiers'` · `(resize modifiers vector origin transform transform-inverse {:keys [precise?]})` · `(rotation modifiers center angle)` · `(add-modifiers a b) → combined`.
**Data Shape:** `(defrecord Modifiers [last-order geometry-parent geometry-child structure-parent structure-child])` — four op vectors + a monotonic counter; each geometric op is `(GeometricOperation. order type vector origin transform transform-inverse rotation center)`.

### Decisive source
```clojure
(defn- maybe-add-resize
  ([operations op {:keys [precise?]}]
   (if (c/empty? operations)
     [op]
     (let [head (peek operations)]
       (if (mergeable-resize? head op)
         (let [item (merge-resize head op)]   ;; vectors MULTIPLY: (* op1-x op2-x)
           (cond-> (pop operations)
             (or precise? (resize-vec? (dm/get-prop item :vector)))
             (conj item)))
         (conj operations op))))))
```

**Flow:** every builder bumps `:last-order` FIRST so parent/child lists share one global timeline → an op whose effect is ~zero (`move-vec?`/`resize-vec?` via `mth/almost-zero?` 1e-4) is silently dropped, keeping drag-time state minimal → consecutive same-type tail ops MERGE in place instead of appending (moves add their vectors; resizes multiply scale factors and only survive merging if still non-trivial, unless `precise?` from pixel-precision mode) → `add-modifiers` concatenates two modifier sets, re-basing incoming orders by `last-order`, and only merges within a lane when the OTHER lane is empty (order consistency guard).
**Invariant:** op order across all four lanes must be reconstructable from `:order` alone — `modifiers->transform` (:646-652) flattens parent+child and `(sort-by #(dm/get-prop % :order) modifiers)` before folding; dropping or reordering ops breaks the final matrix.
**Probe:** `grep -cF '(or precise? (resize-vec? (dm/get-prop item :vector)))' common/src/app/common/types/modifiers.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "maybe-add-resize move-modifiers resize-modifiers rotation-modifiers", limit: 10, fields: ["signature","name","file"] });
```
(verified live: all four builders resolve line-exact at modifiers.cljc)

## Verdict
Adopt "ordered op log + tail-merge + zero-op elision" for any interactive transform tool; adapt the four-lane parent/child × geometry/structure split to your scene graph; omit text-content scaling hooks (`scale-text-content`) if you have no rich-text shapes. Direct test: `common/test/common_tests/types/modifiers_test.cljc` `move-builder`/`resize-builder`/`convenience-builders` (runner blocked honestly in this environment).
