<!-- capsule-v2 -->
# Linvo service taxonomy — how do I structure many LinkedIn actions behind ONE uniform service contract with typed, schedulable errors?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what is the minimal interface every LinkedIn action implements, and how do errors carry machine-actionable retry schedules instead of ad-hoc strings?

## One interface, one registry, three error kinds
**Path/Symbol:** `lib/linkedin/linkedin.services.interface.ts:LinkedinServicesInterface<T>` (:1–6); `lib/linkedin/linkedin.service.ts:services` registry (:12–28); `lib/enums/linkedin.errors.ts:LINKEDIN_ERRORS/LinkedinErrors` (:1–13).
**Signature:** `process: (page: Page, cdp: CDPSession, data?: T) => Promise<any>` — the ONLY member; every action class implements it.
**Data Shape:** `data` is a per-service `RequiredData` literal (e.g. connect = `{message: string; url: string; extra?: {myname, mylastname, mycompany}}`; email/visit = `{url}`); results are plain objects (`{url, linkedin_id}` or extracted fields); failures throw `LinkedinErrors(text, url?, additional?: {values: LINKEDIN_ERRORS, more?: any})`.

### Decisive source
```ts
export enum LINKEDIN_ERRORS { DISCONNECTED, INVALID_CREDENTIALS, DELAY }
export class LinkedinErrors {
  constructor(public text: string, public url?: string,
              public additional?: { values: LINKEDIN_ERRORS; more?: any }) {}
}
// lib/linkedin.service.ts — flat name->instance registry, all extend LinkedinAbstractService
export const services = {
    extract_information: new LinkedinEmailService(), connect: new LinkedinConnectService(),
    message: ..., endorse: ..., like: ..., visit: ..., /* 14 services total */
}
```

**Flow:** caller picks a service by string key → `process(page, cdp, data)` runs the whole action (navigate → wait loaders → act → return payload) → on failure throws `LinkedinErrors`; the enum value tells the scheduler WHAT happened (`DELAY` = pause account, `INVALID_CREDENTIALS` = stop and re-auth, `DISCONNECTED` = session died) and `additional.more` carries HOW LONG (delay in minutes, set by `checkLimit`).
**Invariant:** every action funnels through `process(page, cdp, data?)` — no service invents a second entry signature — and every thrown error is a `LinkedinErrors` carrying an enum value, never a bare string; consumers branch on `values`, not message text. Business-state guards throw BEFORE acting (connect checks "already pending" and email-verification prompts before clicking Connect).
**Probe:** no test suite ships (`test.example.ts` is a stub) — coverage caveat recorded; behavior boundary verified by reading all 14 service classes at HEAD; graph anchors resolve for every `*.process` method.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "LinkedinServicesInterface process LinkedinErrors", limit: 10 });
// resolves all 14 `X.process` implementations + the errors enum
```

## Verdict
Adopt the single-method service interface + flat registry + typed error enum with a machine-readable `more` payload (this is what makes multi-account schedulers possible); adapt the data literals and result shapes to host; omit linvo's concrete business rules you don't share (endorse/like semantics). Runner-up taxonomy: joeyism's BaseScraper hierarchy (see scraper-base-callbacks) solves observability instead of dispatch — compose both when porting.
