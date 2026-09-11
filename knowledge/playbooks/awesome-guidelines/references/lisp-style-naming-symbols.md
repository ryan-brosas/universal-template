<!-- capsule-v2 -->
# Naming — do symbols follow Lisp punctuation conventions?

**Source:** lisp-lang §Naming; Google Lisp §Naming. **Question:** Can readers distinguish specials, constants, and predicates by name alone?

## Symbol seam
**Path/Symbol:** functions, variables, classes in Common Lisp packages.
**Signature:** lowercase hyphenated words; complete unabbreviated names.
**Data Shape:** `*special*`, `+constant+`, predicate `p`/`-p`.

### Decisive pattern
```lisp
(defparameter *db-connection* nil)

(defconstant +default-timeout-seconds+ 30)

(defun user-count (users)
  (length users))

(defun evenp (n)
  (zerop (mod n 2)))

(defun request-throttled-p (request)
  (> (request-rate request) +max-requests-per-minute+))
```

**Flow:** lowercase lisp-case full words → `*earmuffs*` for special variables → `+plus-wrapped+` constants → `wordp` or `multi-word-p` predicates → name by intent not container (`rows` not `string-list` unless generic).
**Invariant:** `userCnt`, `is-even`, `parser-parse-line` (package prefix), or `*MAX*` wrong constant style fails review.
**Probe:** naming review; grep camelCase; package-qualified symbol prefixes inside own package.

## Class naming seam
```lisp
(defclass http-request ()
  ((url :reader request-url :initarg :url :type string)
   (method :reader request-method :initarg :method :type keyword))
  (:documentation "An HTTP request."))
```

**Flow:** class names hyphenated nouns → accessors `protocol-slot` or `class-slot` consistently → no `slot-name-of` accessors.
**Invariant:** `HTTPRequest` mixed case or accessor `url-of` fails review.
**Probe:** CLOS class review checklist on exported API.

## Verdict
lisp-case, *special*, +constant+, p/-p predicates, intent names. Learning note: `lisp-style-learning-note.md`.
