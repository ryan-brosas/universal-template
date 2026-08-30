<!-- capsule-v2 -->
# Layout and namespaces — is formatting uniform and ns hygiene clean?

**Source:** bbatsov Clojure style guide §Source Code Layout, §Namespace Declaration. **Question:** Can readers scan forms and dependencies without hunting files?

## Layout seam
**Path/Symbol:** `.clj` / `.cljs` source files.
**Signature:** 2-space indent; ≤80–120 columns; gathered trailing parens.
**Data Shape:** blank line between top-level forms; no trailing whitespace.

### Decisive pattern
```clojure
(ns myapp.server.routes
  (:require
   [clojure.string :as str]
   [myapp.server.db :as db]))

(defn handle-request
  [request]
  (-> request
      (assoc :started-at (System/nanoTime))
      (db/load-user)
      (str/trim)))
```

**Flow:** spaces not tabs → 2-space body indent → wrap before 80 chars when feasible → gather `)` on closing line → one blank line between `def` forms.
**Invariant:** hard tabs, comma-separated seq literals, or trailing whitespace fail review.
**Probe:** cljfmt / project formatter check; editorconfig `indent_size=2`.

## Namespace seam
```clojure
(ns myorg.mylib.core
  (:require
   [clojure.set :as set]
   [myorg.mylib.util :as util]))
```

**Flow:** multi-segment namespace (`org.project.module`) → one namespace per file → comprehensive `ns` with sorted `:require` → prefer `:as` aliases over `:refer :all` → never `:use` in new code.
**Invariant:** `(ns example)` single-segment library ns or multiple `ns` forms per file fail review.
**Probe:** grep `:use` / `:refer :all`; namespace-segment count ≤5 for libraries.

## Verdict
2-space layout, gathered parens, one ns/file, sorted `:require`. Learning note: `clojure-style-learning-note.md`.
