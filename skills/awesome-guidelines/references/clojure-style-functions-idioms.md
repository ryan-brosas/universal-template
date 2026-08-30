<!-- capsule-v2 -->
# Functions and idioms — are control flow idiomatic and arity bounded?

**Source:** bbatsov Clojure style guide §Functions, §Idioms; contrib guidelines. **Question:** Is code expression-oriented without hidden state or shadowing?

## Control flow seam
**Path/Symbol:** function bodies and higher-order usage.
**Signature:** short functions; `when`/`if-let`; threading macros for pipelines.
**Data Shape:** `:else` in `cond`; pre/post conditions on public API.

### Decisive pattern
```clojure
(defn normalize-email
  [user]
  (when-let [email (:email user)]
    (update user :email str/lower-case)))

(defn process-rows
  [rows]
  (->> rows
       (filter :active?)
       (map :id)
       (set)))
```

**Flow:** prefer `when` over single-branch `if` → `when-let`/`if-let` for bind-and-test → `->`/`->>` for linear transforms → `cond` with `:else` → limit positional params (~5) → add `:pre`/`:post` on tricky public fns.
**Invariant:** nested `if` with one branch, or 10+ positional args without destructuring map, fails review.
**Probe:** function length/arity lint; readability review on threading chains.

## State and shadow seam
```clojure
(defn compute-total [items]
  (reduce + 0 items))

;; not (def cache {}) inside fn body
```

**Flow:** no `def`/`defonce` inside functions for locals → never shadow `clojure.core` without explicit `:exclude` → avoid useless `#()` when `comp`/`partial` clearer → sequence ops over manual `loop/recur` when readable.
**Invariant:** `(def state ...)` inside function or unqualified shadow of `map`/`filter` fails review.
**Probe:** grep `(def ` inside `defn` bodies; clj-kondo shadow warnings.

## Verdict
when/if-let, threading macros, short arity, no inner defs. Learning note: `clojure-style-learning-note.md`.
