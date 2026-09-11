<!-- capsule-v2 -->
# Data and safety — are collections, errors, and macros disciplined?

**Source:** bbatsov Clojure style guide §Data Structures, §Exceptions, §Macros. **Question:** Will data access stay idiomatic and failures explicit?

## Collections seam
**Path/Symbol:** domain data modeled as Clojure collections.
**Signature:** vectors/maps/sets; keywords as map keys.
**Data Shape:** collection-first or keyword-first access; no index loops.

### Decisive pattern
```clojure
(def users
  [{:id 1 :name "Ada"}
   {:id 2 :name "Grace"}])

(defn active-ids [users]
  (->> users
       (filter :active?)
       (map :id)
       (vec)))

(defn lookup-name [users id]
  (get users id))
```

**Flow:** vectors for sequential data → keywords for map keys → `(filter :flag coll)` / `(:key m)` access → convert to vector when random access needed → avoid Java collections/arrays in domain code.
**Invariant:** `(nth coll i)` loops or list literals for growable sequences fail review when vector fits.
**Probe:** grep `(.get` / `aget` in non-interop code; data structure choice in API review.

## Errors and macros seam
```clojure
(defn parse-port [s]
  (let [n (Integer/parseInt s)]
    (when (neg? n)
      (throw (ex-info "port must be non-negative" {:port s})))
    n))

(with-open [rdr (io/reader path)]
  (slurp rdr))

;; function, not macro, when no syntax control needed
(defn square [x] (* x x))
```

**Flow:** `ex-info` or standard Java exception types → `with-open` for resources → catch `Exception`/`ExceptionInfo`, not `Throwable` → macro only when function cannot express syntax → write macro call site before macro definition.
**Invariant:** custom exception deftype without cause, bare `catch Throwable`, or macro replacing trivial function fails review.
**Probe:** clj-kondo linter; test coverage for error paths; macro count audit on new public API.

## Verdict
keyword maps, vectors, ex-info, with-open, functions over macros. Learning note: `clojure-style-learning-note.md`.
