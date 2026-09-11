<!-- capsule-v2 -->
# Single-typed-error budget — how many error TYPES does a scraper facade actually need?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** which failures deserve a type the caller can catch programmatically, and which should stay plain terminal Errors?

## One class, one throw site, everything else plain
**Path/Symbol:** `src/errors.ts:SessionExpired` (:1–7, whole file); sole throw site `src/index.ts:checkIfLoggedIn` (:491); sole caller `setup` (:273); plain-Error sites: constructor option gate ×6 (:180–202), run preflight ×3 (:503–513), teardown-and-rethrow paths setup (:276–283) / run catch (:857–864).
**Signature:** `class SessionExpired extends Error { constructor(message) { super(message); this.name = 'SessionExpired'; Error.captureStackTrace(this, SessionExpired) } }`; thrown as `throw new SessionExpired(errorMessage)` where errorMessage carries the full remediation instruction.
**Data Shape:** graph census (executed this pass): `MATCH (a)-[r:THROWS]->(b)` returns EXACTLY ONE row repo-wide — `checkIfLoggedIn → SessionExpired`. Every other failure is `new Error(...)`.

### Decisive source
```ts
// src/errors.ts — complete
export class SessionExpired extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SessionExpired';
    Error.captureStackTrace(this, SessionExpired)   // elide the class frame from traces
  }
}

// src/index.ts :489–491 — the one typed throw, message = remediation doc
const errorMessage = 'Bad news, we are not logged in! Your session seems to be expired. Use your browser to login again with your LinkedIn credentials and extract the "li_at" cookie value for the "sessionCookieValue" option.';
throw new SessionExpired(errorMessage)
```

**Flow:** the auth probe is the ONLY failure a consumer can act on programmatically (catch ⇒ re-mint `li_at`, then re-setup), so it alone gets a type → its message doubles as operator documentation (exact option name included) → every other error is either thrown synchronously BEFORE any side effect (option gate, preflight — caller state bugs, not runtime conditions) or propagated UNTOUCHED after full teardown (`throw err` rethrows the original, never wrapping or re-classifying) → `captureStackTrace(this, SessionExpired)` keeps stacks pointing at the probe line instead of the trivial wrapper.
**Invariant:** type budget = number of distinct CALLER REACTIONS, not number of failure modes. Here that number is exactly 1. Typed errors must also be honest in stack traces (name stamp + frame elision) and self-documenting in messages. The teardown-rethrow paths preserve error identity — catching `SessionExpired` at the top works precisely because nothing downstream re-wraps it.
**Probe:** deterministic, source-grounded (no test imports SessionExpired — grep over src/ shows it only in index.ts import/throw and errors.ts): `trace_path(checkIfLoggedIn, inbound)` → callers_total = 1 (`setup`); the THROWS Cypher above returns exactly one row; byte-compare of errors.ts against this excerpt matches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "SessionExpired captureStackTrace Error session expired", limit: 5 });
// rank#1 = src.errors.SessionExpired Class src/errors.ts :1–7; also surfaces the __env__LINKEDIN_SESSION_COOKIE_VALUE EnvVar tying auth to the server example
```

## Verdict
Adopt the budget rule: audit your catch sites FIRST; give a class only to failures with a distinct programmatic reaction, and let everything else stay plain synchronous throws or identity-preserving rethrows after cleanup. Adapt message content into your own remediation docs. Omit heavy hierarchies when reactions don't differ — but when ≥3 distinct reactions exist, graduate to `exception-taxonomy-wiring.md`'s subsystem-owned leaf classes (joeyism's 7-class counterpoint) and keep the never-raised-docstring trap from that capsule in mind.

