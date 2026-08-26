<!-- capsule-v2 -->
# Per-test data ownership & middleware isolation tests — what makes test data coupling the enemy, and how do you test middleware without a server?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why must each test add its own DB records, and how can middleware be tested as pure functions?

## Test adds→acts→asserts ONLY its own rows (seed exemption: non-mutating suites); node-mocks-http {req,res} doubles assert statusCode without Express
**Path/Symbol:** `sections/testingandquality/avoid-global-test-fixture.md` (:7 golden rule + seed compromise, :11-19 good example, :28+ anti-pattern with cross-test corruption), `sections/testingandquality/test-middlewares.md` (:7 both objections refuted + pure-function framing, :13-27 httpMocks example).
**Signature:** good: `const siteUnderTest = await SiteService.addSite({name:'siteForUpdateTest'})` inside the Arrange of THE test that uses it; anti-pattern: `before(() => DB.AddSeedDataFromJson('seed.json'))` + tests querying shared `'Portal'`; middleware: `httpMocks.createRequest({method:'GET', url:'/user/42', headers:{authentication:''}})` → `unitUnderTest(request, response)` → `expect(response.statusCode).toBe(403)`.
**Data Shape:** fixture scope = per-test rows vs global seed file; middleware doubles = synthetic {req,res} objects with interaction spying.

### Decisive source
```javascript
// avoid-global-test-fixture.md :50 — the failure mode of shared seeds
it('When querying by site name, get the right site', async () => {
  //Act - I know that site name 'portal' exists - I saw it in the seed files
  const siteToCheck = await SiteService.getSiteByName('Portal');
  expect(siteToCheck.name).to.be.equal('Portal'); //Failure! The previous
  //test change the name :[
```

**Flow:** each test seeds exactly what it acts on → assertions can only observe that test's own writes → order-independence for free → when performance genuinely hurts, seed ONLY non-mutating query suites (:7 compromise) → middlewares bypass the server entirely: invoke the function with mocked {req,res} and spy on what it sets.
**Invariant:** "I saw it in the seed files" knowledge is hidden coupling — a prior test's mutation breaks a LATER test's assertion (the :50 comment is the whole argument). Middleware smallness never justifies skipping tests: they "affect all or most of the requests" (:7). Complements pass-1's `aaa-test-structure` (this is the Arrange-ownership rule) and `five-outcomes-test-coverage`.
**Probe:** no runner upstream. Deterministic probe: `grep -cF 'seed.json' sections/testingandquality/avoid-global-test-fixture.md` >= 2 && `grep -c 'createRequest' sections/testingandquality/test-middlewares.md` >= 1 && `grep -c node-mocks-http sections/testingandquality/test-middlewares.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "node-mocks-http", limit: 5 });`

## Verdict
Adopt per-test data ownership as default and the query-suite-only seeding exception; adopt httpMocks-style middleware unit tests before any e2e. Adapt in-memory DB choice for speed. Omit nothing.
