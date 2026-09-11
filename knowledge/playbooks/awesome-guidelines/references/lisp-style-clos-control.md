<!-- capsule-v2 -->
# CLOS and control flow — are objects and conditionals idiomatic?

**Source:** lisp-lang §CLOS, §Flow Control; Google Lisp §CLOS. **Question:** Are classes documented and conditionals readable?

## CLOS seam
**Path/Symbol:** exported classes and generic functions.
**Signature:** typed slots; readers; `defgeneric` for protocols.
**Data Shape:** slot option order: accessor, initarg, initform, type, documentation.

### Decisive pattern
```lisp
(defgeneric request-url (request)
  (:documentation "URL of the HTTP request."))

(defclass request ()
  ((url :reader request-url
        :initarg :url
        :type string
        :documentation "Request URL.")
   (method :reader request-method
           :initarg :method
           :initform :get
           :type keyword
           :documentation "HTTP method keyword."))
  (:documentation "A general HTTP request."))
```

**Flow:** `defgeneric` + docstring for exported protocol → slot `:type` when possible → use readers/`with-accessors` not `slot-value` in app code → generic functions share a protocol, not random overload names.
**Invariant:** undocumented exported `defmethod` without `defgeneric`, or `slot-value` in domain code, fails review.
**Probe:** CLOS API review; SBCL style warnings on `defgeneric` keyword args.

## Control flow seam
```lisp
(defun rocket-ready-p (rocket)
  (and (fuelledp rocket)
       (every #'strapped-in-p (crew rocket))
       (sensors-working-p rocket)))

(defun launch-if-ready (rocket)
  (if (rocket-ready-p rocket)
      (launch rocket)
      (error "Aborting launch: ~A" rocket)))
```

**Flow:** extract complex `and`/`or` to predicate → `when`/`unless` for single-branch cases → `cond` with multiple branches → docstrings on exported functions/packages/classes.
**Invariant:** 15-line condition inside `if` or `(if (not ...))` without `unless` fails review.
**Probe:** function length/condition complexity review; docstring coverage on exports.

## Verdict
typed CLOS slots, defgeneric protocols, when/unless, factored predicates. Learning note: `lisp-style-learning-note.md`.
