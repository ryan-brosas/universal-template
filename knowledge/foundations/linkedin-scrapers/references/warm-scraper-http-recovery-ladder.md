<!-- capsule-v2 -->
# Warm-scraper HTTP recovery ladder — how do you expose a stateful warm scraper behind HTTP so one failed request neither kills the process nor leaves an undead service?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125` (express `^4.17.1`, devDependency); Codebase Memory `linkedin-profile-scraper-api`. **Question:** what does the upstream example actually guarantee when `run()` rejects inside a route — and what must a porter ADD?

## The example's shape, then its terminal gap
**Path/Symbol:** `src/examples/server.ts` (:1–29, whole file); failure semantics owned by `src/index.ts:LinkedInProfileScraper.run` catch (:857–864), preflight (:503–513), and `close` (:416–460).
**Signature:** module-scope `new LinkedInProfileScraper({ sessionCookieValue: process.env.LINKEDIN_SESSION_COOKIE_VALUE, keepAlive: true })`; `await scraper.setup()` inside an async IIFE BEFORE `app.listen(process.env.PORT || 3000)`; ONE handler: `app.get('/', async (req, res) => res.json(await scraper.run(req.query.url)))`.
**Data Shape:** GET `/?url=<profile-url>` → JSON aggregate `{userProfile, experiences, education, volunteerExperiences, skills}`; on failure NOTHING is defined — no error status, no error middleware, no retry.

### Decisive source
```ts
// src/examples/server.ts (complete handler — note what is ABSENT)
app.get("/", async (req, res) => {
  const urlToScrape = req.query.url as string;
  const result = await scraper.run(urlToScrape);
  return res.json(result);
});
app.listen(process.env.PORT || 3000);

// src/index.ts run() catch — teardown THEN rethrow
} catch (err) {
  await this.close()          // FULL teardown: browser.close() + treeKill SIGKILL
  statusLog(logSection, 'An error occurred during a run.')
  throw err;                  // Express 4 never sees this rejection
}
```

**Flow:** setup-before-listen wires the auth probe into boot (bad cookie dies at startup, not per-request) → every request rides the warm browser through `run()` → on ANY failure run()'s own catch tears down the WHOLE browser first, then rethrows → Express 4 does not forward async-handler rejections to error middleware (no `next(err)` exists anywhere in the file), so the rejection becomes an unhandledRejection (process-fatal on Node ≥15 defaults) → if anything survives that, `this.browser === null` permanently (only `setup()` reassigns it), so every later request hits the preflight `throw new Error('Browser is not set. Please run the setup method first.')` (:503–505).
**Invariant:** one failed request is TERMINAL for a warm session under this wrapper — crash (Node ≥15) or zombie (`browser=null` service that answers every request with the same setup error). A port MUST add the ladder upstream lacks: (1) try/catch INSIDE each async handler mapping typed errors to statuses (`SessionExpired` → 401-style "re-mint li_at"; preflight errors → 400/503); (2) a recovery step that re-runs `setup()` after any full-teardown failure, because close() nulled the browser and nothing else restores it; (3) optionally an `unhandledRejection` guard so telemetry records the gap instead of dying silently.
**Probe:** deterministic, source-grounded (no test exercises express anywhere in src — grep-verified): server.ts has zero `try`/`catch` tokens and zero `next` references; run()'s rethrow at :864 is the ONLY exit from its catch; `close()` sets `this.browser = null` before rethrow paths can return. Chain: rejection ⇒ close() ⇒ browser null ⇒ next request throws :504 byte-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "express server scraper setup listen profile url", limit: 6 });
// resolves the owning lifecycle methods (setup/run/close/constructor); server.ts itself is an IIFE with no extracted Function nodes
```

## Verdict
Adopt the wrapper skeleton: module-scope warm instance, env-fed cookie, setup-before-listen, one thin route. Do NOT adopt its absence of error handling — port the three-rung ladder above. Contrast `warm-browser-service-contract.md` (the happy-path economics this wrapper rides), `zombie-browser-teardown.md` (why close() is safe to call from the catch), and `full-response-transport-kernel.md` (private-api's CLIENT-side "error handling deliberately absent" — same instinct, different layer; there the caller owns retries, here NOBODY does).

