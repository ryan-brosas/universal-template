<!-- capsule-v2 -->
# Data helpers — sentinel-guarded conditional updates and transient-based concat

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** Why does penpot's `update-in-when` use a sentinel object instead of nil-checking, and when do its concat variants outperform `into`?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/data.cljc` : `sentinel`/`getf`/`update-vals` (:496-510), `update-in-when`/`update-when`/`assoc-in-when` (:512-531), `concat-vec`/`concat-set` + `transient-concat` (:232-257), `deep-merge`/`dissoc-in` (:195-212).
**Signature:** `(update-in-when m key-seq f & args)` · `(concat-vec c1 & more)`.
**Data Shape:** `sentinel` is a fresh `(Object.)` per runtime — the "key absent" witness distinct from every stored value including nil.

### Decisive source
```clojure
(def sentinel #?(:clj (Object.) :cljs (js/Object.)))

(defn update-in-when [m key-seq f & args]
  (let [found (get-in m key-seq sentinel)]
    (if-not (identical? sentinel found)
      (assoc-in m key-seq (apply f found args))
      m)))                                   ;; path missing → return m UNCHANGED

(defn concat-vec
  ([] [])
  ([c1] (if (vector? c1) c1 (into [] c1)))
  ([c1 & more]
   (if (vector? c1)
     (transient-concat c1 more)              ;; fast path: no re-copy when already a vector
     (transient-concat [] (cons c1 more)))))
```

**Flow:** `update-in-when` is used by EVERY change processor method (`d/update-in-when data [:pages-index page-id] …`) so a change aimed at a missing page/component is a silent no-op instead of an NPE — that tolerance is what makes change replays idempotent-safe → `identical?` comparison matters: a stored `nil` at the path must still be updated, so equality-by-value (`=`) would be wrong → `deep-merge` recurses only when the LEFT side is a map, so vectors/scalars replace wholesale.
**Invariant:** absence ≠ nil in these helpers; any port that substitutes `(when-not found …)` corrupts documents that legitimately store nil values.
**Probe:** `grep -cF 'if-not (identical? sentinel found)' common/src/app/common/data.cljc` → 4 (update-in-when :515, update-when :522, assoc-in-when :529, assoc-when :536).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "update-in-when update-when assoc-in-when getf deep-merge dissoc-in", limit: 10, fields: ["signature","name","file"] });
```
(verified live: `…data.update-in-when Function common/src/app/common/data.cljc 512-517`)

## Verdict
Adopt sentinel-guarded conditional updates for any schema-evolving document where processors must tolerate stale paths; adapt `transient-concat` only if profiling shows concat cost; omit lazy `mapcat`/`concat-all` variants unless hot paths demand them. Coverage caveat: data.cljc is 1289 lines with many more helpers — this capsule mines only the document-safety core.
