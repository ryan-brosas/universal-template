<!-- capsule-v2 -->
# Undo stack — how do you bound undo history without losing the redo branch?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** What is the minimal correct bounded undo/redo stack (100 entries) that handles append-after-undo, duplicate suppression, and nil stacks?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/data/undo_stack.cljc` : whole file (:15-60, 60 lines).
**Signature:** `(make-stack)` · `(append stack value)` · `(undo stack)` · `(redo stack)` · `(peek stack)` · `(size stack)`.
**Data Shape:** plain map `{:index int :items vector}` — index points at the CURRENT state; everything above it is the redo branch.

### Decisive source
```clojure
(defn append [{index :index items :items :as stack} value]
  (if (and (some? stack) (not= value (peek stack)))
    (let [items (cond-> items
                  (> index 0)
                  (subvec 0 (inc index))          ;; DROP the redo branch first

                  (> (+ index 2) MAX-UNDO-SIZE)
                  (subvec 1 (inc index))          ;; then evict OLDEST to stay under 100

                  :always
                  (conj value))
          index (min (dec MAX-UNDO-SIZE) (inc index))]
      {:index index :items items})
    stack))                                       ;; duplicate or nil stack → unchanged

(defn undo [stack] (update stack :index #(max 0 (dec %))))
(defn redo [{:keys [index items] :as stack}]
  (cond-> stack (< index (dec (count items))) (update :index inc)))
```

**Flow:** append → suppress exact duplicates (`not= value (peek)`) → truncate anything above current index (redo branch dies the moment you act) → evict from the FRONT when full → conj and advance index clamped to `MAX-UNDO-SIZE-1`. Undo/redo are pure index moves; `fixup` (:44-46) replaces the current top in place (used to amend the live entry).
**Invariant:** `:index` is a cursor into a persistent vector — size is `(inc index)`, never `(count items)` after an undo. Appending while undone MUST discard the redo branch or redo replays stale futures.
**Probe:** `grep -cF '(min (dec MAX-UNDO-SIZE) (inc index))' common/src/app/common/data/undo_stack.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "MAX-UNDO-SIZE make-stack fixup", limit: 10, fields: ["signature","name","file"] });
```
(verified live: `…data.undo_stack.MAX-UNDO-SIZE … common/src/app/common/data/undo_stack.cljc 13`)

## Verdict
Adopt verbatim (60 lines, zero deps) for any editor needing bounded history with branch discard; adapt entry payload to your change units; omit nothing — this is the whole primitive. Tests: `undo_stack_test.cljc` covers nil-stack, duplicate suppression, undo-then-append (runner blocked honestly).
