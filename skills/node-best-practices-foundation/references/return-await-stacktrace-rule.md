<!-- capsule-v2 -->
# Return-await stacktrace rule — the three shapes that punch holes in async stack traces, and why you never remove `return await` for performance

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** When exactly does V8 drop frames or call sites from an async stack trace, what is the mechanical fix for each shape, and why is removing `return await` the wrong performance move?

## Three hole-shapes: un-awaited return, sync-returner, async-callback-in-sync-slot
**Path/Symbol:** `sections/errorhandling/returningpromises.md` (explainer :7, AP#1 :11-24, correct :39-51, AP#2 sync-returner :60-90, AP#3 :142-173, AP#3 fix :175-205, advanced explanation :235-244, tradeoff :246-254, no-return-await history :257-263).
**Signature:** `async function f() { return await inner(); }` — NOT `return inner();`; sync functions returning promises must become `async`; callbacks passed to sync APIs wrapped: `userIds.map(async id => await getUser(id))` — NOT `userIds.map(getUser)`.
**Data Shape:** three failure shapes, each losing a different piece of the trace: (1) `return promise` without await → the intermediate function's frame vanishes; (2) a SYNC function returning a promise → its frame always vanishes once any async op follows (only `async` functions may `await`, so sync frames can never join the promise-resolution chain, :235-244); (3) an async callback handed where a sync callback is expected (`map(getUser)`) → the CALL SITE vanishes — the stack shows `getUser` and `Promise.all (index N)` but no clue where it was called (and `(index N)` is a v8-internal line, not your code, per the cited v8 bug :160-166).

### Decisive source
```text
// returningpromises.md :7 — the mechanism
There is a v8 feature called "zero-cost async stacktraces" that allows
stacktraces to not be cut on the most recent `await`. But due to
non-trivial implementation details, it will not work if the return value
of a function (sync or async) is a promise.
// :198 — the AP#3 fix: explicit await in the wrapper names the call site
Promise.all(userIds.map(async id => await getUser(id))).catch(console.log)
// :248-253 — the tradeoff that kills premature de-awaits
Every `await` creates a new microtask in the event loop, so adding more
`await`s to the code would introduce some performance penalty. Nevertheless,
the performance penalty introduced by network or database is tremendously
larger ... So removing `await`s in `return await`s should be one of the last
places to search for noticeable performance boost and definitely should
never be done up-front
```

**Flow:** caller awaits f → f must itself await the inner promise before returning → on rejection the stack shows caller → f → origin. Shape 2: make the returning function `async` so it CAN await. Shape 3: when you cannot change the API that calls the callback (backward compatibility), wrap the async fn in a dummy async arrow whose explicit `await` puts the exact call site back into the trace (:175-205). History check before linting: old `no-return-await` rules flagged `return await` because pre-zero-cost-stacktraces (Node <10, unflagged in 12) it was equivalent to plain `return` outside try blocks — on modern Node it is NOT redundant, and the practice is Node-specific, "not for ECMAScript in general" (:257-263).
**Invariant:** every function that returns a promise must be declared `async` AND explicitly await it before returning; every async callback passed into a sync slot gets a dummy-async wrapper with an explicit await. Related micro-rule in the same doc (:18): inside a genuinely-async body use `await null` to force true asynchronicity when nothing else needs awaiting. Performance rule: removing `return await` is a LAST-resort micro-optimization, never an up-front choice — the microtask cost is noise next to network/DB latency.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'return await' sections/errorhandling/returningpromises.md` ≥ 1 && `grep -c 'map(async id => await getUser(id))' sections/errorhandling/returningpromises.md` = 1 && `grep -c 'microtask' sections/errorhandling/returningpromises.md` = 1 && `grep -c 'no-return-await' sections/errorhandling/returningpromises.md` = 1.
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "dummy async function", "limit": 5}'
# EXACTLY 1 result: returningpromises.md Section node 175-176 (the AP#3 fix heading; verified 2026-08-26)
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "return await", "limit": 10}'
# resolves `sections/errorhandling/returningpromises.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt all three fixes as lintable invariants for any async runtime (the rationale generalizes beyond V8). Adapt wording per engine; note some lint rules flag redundant awaits — this doc records WHY they are not redundant here, and why the historical `no-return-await` ban predates zero-cost async stacktraces. Omit version-specific V8 internals except the one load-bearing fact: only `async` functions can join the promise-resolution chain.
