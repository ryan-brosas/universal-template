<!-- capsule-v2 -->
# Client field-precedence wiring — why must composite clients let children defer reading parent links until first call?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** when a Client wires five repositories + login as class fields that capture `this`, what is initialized when — and what would a porter break?

## Two-layer composition, one ordering trap
**Path/Symbol:** `src/core/client.ts:Client` (:16-35); `src/core/linkedin-request.ts:LinkedInRequest` (:9-20).
**Signature:** `class Client { request: LinkedInRequest; constructor({ proxy }: ClientOpts = {}) { this.request = new LinkedInRequest({ proxy }); } login = new Login({ client: this }); search = new SearchRepository({ client: this }); … }`.
**Data Shape:** layer 1 — `Client` owns `request` plus feature repos (search/invitation/profile/conversation/message) and `login`; layer 2 — each repository receives `{ client }`, and `LinkedInRequest` fans out to six Request children (`auth/conversation/invitation/message/profile/search`) receiving `{ request: this }`.

### Decisive source
```ts
export class Client {
  request: LinkedInRequest;                    // NOT initialized here

  constructor({ proxy }: ClientOpts = {}) {
    this.request = new LinkedInRequest({ proxy });   // ← ctor BODY…
  }

  login = new Login({ client: this });          // …runs AFTER these field
  search = new SearchRepository({ client: this }); // initializers
```

**Flow:** instance fields with initializers execute in declaration order BEFORE the constructor body statements — so `Login` and all five repositories are constructed while `client.request` is still `undefined`; only afterwards does the body assign `this.request`. Nothing crashes because children merely STORE the parent reference and touch it exclusively inside methods (e.g. `SearchRepository.fetchJobs` reads `this.client.request.search…` at call time). Same pattern repeats one level down: `LinkedInRequest` field-initializes its six Request children against `this`.
**Invariant:** children MUST NOT read a parent link during their own construction — the wiring order guarantees `undefined` there; any eager read in a constructor (validation, prefetch, scroller warmup) throws. Declaration order IS initialization order (`login` first). Repositories additionally act as factories: they build scrollers lazily per call, not at wiring time.
**Probe:** no dedicated constructor test exists; `test/login/login.spec.ts` + `test/search/search-repository.spec.ts` dynamic-import `Client` and stub by exact URL+params (see `testdouble-mock-harness` capsule) — proving the whole surface is exercisable through method calls only, i.e. deferred reads suffice. `check_index_coverage` on `src/core/client.ts` = `no_recorded_issue`+`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "Client constructor repository wiring", limit: 6 });
```

## Verdict
Adopt the two-layer composite (feature façade → transport hub) and the lazy-read rule for `this`-capturing field wiring in ANY language with declarative member initializers (TS/JS/Kotlin/Swift all share the ordering semantics). Adapt the repository set to your domain. Omit nothing behavioral — the trap itself is the payload.
