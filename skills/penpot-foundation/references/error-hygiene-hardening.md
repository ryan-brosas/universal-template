<!-- capsule-v2 -->
# Error-hygiene hardening — how do you stop 500 bodies from leaking internals without losing the error protocol?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (dd4a163 "Remove internal error details from HTTP error responses" + 7c85837 logout fix); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** Which fields of an error envelope leak implementation details, and what replaces them for database errors specifically?

## strip-internal-fields + SQLSTATE message table
**Path/Symbol:** `backend/src/app/http/errors.clj` (`strip-internal-fields` :37-41, applied at :145/:171/:239; `pgsql-state->message` :188-200; PSQLException handler :202-226; `:default` exception handler :228-248; IOException handler :250-256; `handle` dispatcher :272-277) + direct tests `backend/test/backend_tests/http_middleware_test.clj` (:379-443).
**Signature:** `(strip-internal-fields data) -> data'` = `(dissoc data :state :path :context)`; `(pgsql-state->message state) -> string`.
**Data Shape:** error body map `{... :type :server-error :code keyword :hint string?}`; `handle-error` multimethods dispatch on `(:type (ex-data cause))`, `handle-exception` on exception CLASS.

### Decisive source
```clojure
(defn- strip-internal-fields
  "Remove fields that leak internal implementation details from error
   response data. Full context is preserved in server-side logs."
  [data]
  (dissoc data :state :path :context))

(case state
  "23505" "A conflicting entry already exists"
  "23503" "The referenced item does not exist"
  "23502" "A required field is missing"
  "23514" "The value violates a data integrity constraint"
  "57014" "The operation took too long and was cancelled"
  "25P03" "The transaction was idle too long and was cancelled"
  "A database error occurred")
```

**Flow:** the PSQL handler previously echoed `(ex-message error)` and even the raw `:state` — now every arm maps SQLSTATE → fixed copy, `57014/25P03` keep status 504 with their own codes (`:statement-timeout` / `:idle-in-transaction-timeout`), everything else collapses to ONE code `:database-error` + 500. The generic handlers apply `strip-internal-fields` at three sites (`:assertion`, `:internal`, `:default`) while PRESERVING `:hint` when it's part of the deliberate protocol (e.g. validation errors raise curated hints like `"invalid JSON in request body"` — middleware.clj now uses FIXED hint strings instead of `(ex-message cause)`), and DROP `:hint` where it used to echo raw messages (IOException / unhandled Throwable now return no hint at all).
**Invariant:** `:hint` has two regimes that must not be confused: CURATED protocol hints (validation family) survive; RAW exception-message hints were eliminated everywhere. Server logs still get full context via `l/*context*` binding — stripping is response-only. Unknown SQLSTATE falls through to a generic default (the trailing `case` expression), never an exception.
**Probe:** direct tests pin all three behaviors byte-exact: `internal-error-strips-sensitive-fields` (:403-421) asserts `:state/:path/:context` nil while `:hint` survives; `unhandled-exinfo-strips-sensitive-fields` (:423-441) same for the default path; updated legacy tests assert `(= "boom"-style hints → nil?)` at :382/:402 and exact curated strings at :305/:324/:342. Grep anchor from repo root: `grep -c 'strip-internal-fields' backend/src/app/http/errors.clj` → 4 (:37 def + three call sites).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"handle-error strip-internal-fields pgsql-state","limit":5,"detail":"ids"}'
```
(rank 1-2: `strip-internal-fields` 37-41, `pgsql-state->message` 188-200.)

## Verdict
Adopt the three-field strip list, the SQLSTATE→copy table with class-based fallback, and the two-regime hint rule. Adapt codes/copy to your API surface. Omit Penpot's yeti/response plumbing.
