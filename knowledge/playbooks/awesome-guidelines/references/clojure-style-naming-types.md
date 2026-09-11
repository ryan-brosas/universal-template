<!-- capsule-v2 -->
# Naming — do symbols follow Clojure conventions?

**Source:** bbatsov Clojure style guide §Naming; Clojure contrib guidelines. **Question:** Can readers tell predicates, side effects, and types apart by name?

## Function and var seam
**Path/Symbol:** public and private vars in application/library code.
**Signature:** lisp-case functions; `?` predicates; `!` side effects; `*earmuffs*` dynamics.
**Data Shape:** `CapitalCase` for records/protocols/deftype.

### Decisive pattern
```clojure
(def ^:private +default-timeout-ms+ 5000)

(def ^:dynamic *db-connection* nil)

(defn palindrome?
  [s]
  (= s (str/reverse s)))

(defn save-user!
  [user]
  (db/insert! user))

(defrecord HttpRequest [method path headers])
```

**Flow:** kebab-case (`lisp-case`) for functions/vars → `?` suffix on predicates → `!` on STM-unsafe/side-effecting fns → `*name*` for dynamic vars → `CapitalCase` types with acronym caps preserved (`HTTP`, `XML`).
**Invariant:** `isValid`, `save_user`, or `palindrome-p` naming fails review.
**Probe:** clj-kondo unresolved symbol + naming cops; code review checklist.

## Namespace naming seam
**Flow:** `organization.project.module` or `project.module` → kebab-case segments (`bruce.project-euler`) → library single-ns may use `project.core` only when truly one implementation ns.
**Invariant:** `my_lib.util` snake_case namespace segments fail review.
**Probe:** namespace declaration matches directory path (`myapp/server/routes.clj` → `myapp.server.routes`).

## Verdict
lisp-case, CapitalCase types, ?/!/earmuff conventions. Learning note: `clojure-style-learning-note.md`.
