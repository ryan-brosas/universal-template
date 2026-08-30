<!-- capsule-v2 -->
# Packages and systems — are namespaces explicit and ASDF metadata complete?

**Source:** lisp-lang §Packages, §Project Structure; Google Lisp §Packages. **Question:** Can consumers import only what they need without `::` hacks?

## Package seam
**Path/Symbol:** `defpackage` forms and ASDF system definitions.
**Signature:** hierarchical package names; `:import-from` over `:use`.
**Data Shape:** one primary package per file; exported externals only.

### Decisive pattern
```lisp
(defpackage :spider.http.request
  (:use :cl)
  (:import-from :alexandria
                :curry
                :with-gensyms)
  (:export #:parse-request-line
           #:request-url
           #:request-method))

(in-package :spider.http.request)
```

**Flow:** `org.project.module` hierarchy → `:use :cl` only by default → explicit `:import-from` for deps → `:export` public API → never reference `pkg::internal` in production (export or split impl package).
**Invariant:** `(defpackage :foo (:use :cl :alexandria :drakma))` or app code `other::secret` fails review.
**Probe:** grep `::` in `src/` (allow tests if documented); package use audit.

## ASDF seam
```lisp
(defsystem "spider"
  :author "Ada Lisper <ada@example.com>"
  :license "MIT"
  :version "0.1.0"
  :depends-on (:alexandria :clack)
  :components ((:module "src"
                :serial t
                :components ((:file "request"))))
  :description "Web scraping framework."
  :in-order-to ((test-op (test-op "spider-test"))))
```

**Flow:** separate `project.asd` and `project-test.asd` → metadata `:author`, `:license`, `:version`, `:homepage` → components mirror package hierarchy → `.asd` files contain systems only, not application logic.
**Invariant:** code in `.asd` or monolithic single package for large app without hierarchy fails review.
**Probe:** `asdf:load-system` + `asdf:test-system` in CI.

## Verdict
hierarchical packages, import-from, no ::, ASDF metadata + tests. Learning note: `lisp-style-learning-note.md`.
