<!-- capsule-v2 -->
# Return-await stacktrace rule — why does `return someAsync()` punch a hole in the stack trace?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** When exactly does V8 drop the calling function from an async stack trace, and what is the mechanical fix?

## Always `return await` from async functions
**Path/Symbol:** `sections/errorhandling/returningpromises.md` (explainer :7, anti-pattern :11-24, correct :39-51).
**Signature:** `async function f() { return await inner(); }` — NOT `return inner();`.
**Data Shape:** input: any async (or sync) function whose return value is a promise. Failure shape when violated: rejection stack contains the frame that CREATED the promise and the awaiting caller, but skips the intermediate function — precisely where diagnosis often needs to look.

### Decisive source
```text
// returningpromises.md :7 — the mechanism
There is a v8 feature called "zero-cost async stacktraces" that allows
stacktraces to not be cut on the most recent `await`. But due to
non-trivial implementation details, it will not work if the return value
of a function (sync or async) is a promise.
// :51 — the fix
return await throwAsync('with all frames present')
```

**Flow:** caller awaits f → f must itself await the inner promise before returning → on rejection the stack shows caller → f → origin. If f merely returns the promise, f's frame vanishes; if the bug lives in f's own post-return logic or parameters, the missing frame hides the cause.
**Invariant:** every function that returns a promise must be declared `async` AND explicitly await it before returning. Related micro-rule in the same doc (:18): inside a genuinely-async body use `await null` to force true asynchronicity when nothing else needs awaiting.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'return await' sections/errorhandling/returningpromises.md` ≥ 1 with the zero-cost-async-stacktraces explanation paragraph present.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "return await", "limit": 10}'
# resolves `sections/errorhandling/returningpromises.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt `return await` as a lintable invariant for any async runtime (the rationale generalizes beyond V8). Adapt wording per engine; note some lint rules flag redundant awaits — this doc records WHY they are not redundant here. Omit version-specific V8 internals.
