<!-- capsule-v2 -->
# ObjectsMap — can a document map serialize per-field without decoding the whole map?

**Source:** penpot MPL-2.0 `develop@dd6b521b`; Codebase Memory `ext-penpot`. **Question:** How does penpot store tens of thousands of shapes so the backend can persist/decode only dirty fields while frontend reads stay transparent?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/types/objects_map.cljc` : `deftype ObjectsMap` (CLJS :159-336 / CLJ :338-459) + `do-compact`/`from-data`/`wrap` (:464-505) + fressian/transit handlers (:507-521).
**Signature:** `(-lookup this k)` · `(-assoc this k v)` · `(compact this)` · `(from-data data)` · `(wrap objects)`.
**Data Shape:** two parallel maps — `data` holds ENCODED transit strings (nil placeholder for entries not yet persisted) and `cache` holds DECODED values; mutable `modified` flag tracks dirtiness.

### Decisive source
```clojure
(c/ILookup
 (-lookup [this k]
   (or (c/-lookup cache k)
       (if (c/-contains-key? data k)
         (let [v (t/decode-str (c/-lookup data k))]
           (set! (.-cache this) (c/-assoc cache k v))     ;; decode-on-read memoization
           v)
         (do (set! (.-cache this) (assoc cache k nil))    ;; NEGATIVE lookup memoized too
             nil)))))
(-assoc [_ k v]
  (ObjectsMap. metadata (c/-assoc cache k v) (c/-assoc data k nil) true nil))  ;; encode DEFERRED

(defn- do-compact [data cache update-fn]
  (let [new-data (persistent!
                  (reduce-kv (fn [data id obj]
                               (if (nil? obj)
                                 (assoc! data id (t/encode-str (get cache id)))
                                 data))
                             (transient data) data))]
    (update-fn new-data) nil))
```

**Flow:** read → hit cache or lazily decode from `data` and memoize (even misses are cached as nil, so repeated lookups of absent ids cost nothing) → assoc/dissoc update BOTH maps but leave `data[k]` as a nil tombstone with `modified=true` → `compact()` (explicit or before serialization via `get-data`) re-encodes ONLY tombstoned entries into transit strings. Fressian tag `"penpot/objects-map/v2"` writes the compacted `data`; transit handler mirrors it.
**Invariant:** `data` keys are membership truth; values may be stale/nil until compaction — equality, iteration, and hash all route through lazy entry objects that decode on demand. A porter who encodes eagerly loses the whole point (per-field persistence), one who skips negative caching re-decodes absent keys forever.
**Probe:** `grep -cF '(set! (.-cache this) (assoc cache k nil))' common/src/app/common/types/objects_map.cljc` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-penpot", query: "ObjectsMap objects-map do-compact from-data wrap", limit: 10, fields: ["signature","name","file"] });
```
(verified live: `ObjectsMap Struct backend/src/app/util/objects_map.clj 77-343` + common twin; note BM25 ranks the backend twin high — cite THIS path.)

## Verdict
Adopt the dual-map lazy-codec pattern for any large collaborative doc store needing partial serialization; adapt codec (penpot uses transit/fressian); omit CLJ reflection-tuning and JSON writer plumbing. Tests: `objects_map_test.cljc` basic-operations/transit-encode-decode (runner blocked honestly). Backend twin `backend/src/app/util/objects_map.clj` exists for JVM-only contexts.
