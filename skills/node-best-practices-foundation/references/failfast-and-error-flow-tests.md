<!-- capsule-v2 -->
# Fail-fast argument validation & error-flow testing — why validate inputs eagerly, and how do you TEST the failure paths?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What's the minimal validation posture at function entry, and which three failure surfaces must tests cover?

## Joi.assert throws before logic; tests pin thrown-type, HTTP-error+logged-fields, and uncaughtException routing
**Path/Symbol:** `sections/errorhandling/failfast.md` (:5 rationale, :13-24 Joi.assert example, :65-68 Joyent throw-immediately), `sections/errorhandling/testingerrorflows.md` (:5 coverage premise, :13-19 throw-type test, :30-53 HTTP-error + logged-fields test, :64-75 uncaughtException test), `sections/errorhandling/asyncerrorhandling.md` (:5 callback-nesting rationale, :10-16 promise chain, :22-34 try/catch/finally ladder, :91 stack-loss quote).
**Signature:** `Joi.assert(newMember, memberSchema)` (throws on violation, FIRST line of function); sinon `stub(...).rejects(new AppError("saving-failed", ..., 500))`; assert `loggerDouble.lastCall.firstArg` matches `{name, status:500, stack, message}`; trigger via `process.emit("uncaughtException", errorToThrow)`.
**Data Shape:** validation = schema objects at entry; error-flow tests = 3 layers — unit (thrown constructor), API (status code + logger payload shape), process (uncaughtException handler).

### Decisive source
```javascript
// testingerrorflows.md :47-52 — the logged-fields contract most ports forget
expect(loggerDouble.lastCall.firstArg).toMatchObject({
  name: "saving-failed",
  status: 500,
  stack: expect.any(String),
  message: expect.any(String),
});
// :71 — driving the process-level funnel deterministically
process.emit("uncaughtException", errorToThrow);
```

**Flow:** arguments validated against schema at function start (assertions come FIRST, :22) — degenerate inputs throw immediately with a stack ("the program is broken", Joyent :65-68) → async flows use promise chains / async-await so ONE `.catch()` owns errors instead of per-callback `if(err !== null)` pyramids (callbacks "deprive us of the stack" :91) → tests then verify all three surfaces, including that the logger receives the MANDATORY fields (name/status/stack/message) on the error path.
**Invariant:** happy-path-only testing gives zero trust exceptions are handled (:5). A negative discount slipping past validation redirects real users (:35-44 anti-pattern) — undefined-vs-value confusion is the canonical miss. The uncaughtException test proves the funnel from `unhandled-rejection-funnel`/`centralized-handler-not-middleware` actually fires.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'Joi.assert' sections/errorhandling/failfast.md` >= 1 && `grep -cF 'process.emit("uncaughtException"' sections/errorhandling/testingerrorflows.md` >= 1 && `grep -c '.catch((err)' sections/errorhandling/asyncerrorhandling.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "Joi.assert", limit: 5 });`

## Verdict
Adopt entry-validation-before-logic, the promise/async error rails, and the three-layer error-flow test suite verbatim (it's the missing test plane of pass-1's AAA/five-outcomes capsules). Adapt schema library (zod/yup equivalents). Omit Bluebird/Q era notes — native promises supersede.
