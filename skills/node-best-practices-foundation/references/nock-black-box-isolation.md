<!-- capsule-v2 -->
# Nock black-box isolation — how do you mock external HTTP so the unit under test never touches the real network?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What is the correct nock setup to isolate a component AND simulate non-happy paths AND prevent accidental real calls?

## Intercept at the network layer, fail-closed on unknown calls
**Path/Symbol:** `sections/testingandquality/mock-external-services.md` (explainer :3, intercept :7-12, scenario :14-27, fail-closed :29-35, schema-assert :37-52).
**Signature:** `nock(host).get(path).reply(status, body)`; `nock.disableNetConnect()` + `nock.enableNetConnect("127.0.0.1")`; capture-and-assert via a reply interceptor that stores the payload.
**Data Shape:** each interceptor maps a method+path to a canned response. The fail-closed pair makes ANY un-intercepted outbound call throw instead of leaking to the real world.

### Decisive source
```javascript
// mock-external-services.md :29-35 — fail-closed isolation
beforeAll(async () => {
  // Ensure this component is isolated by preventing unknown calls
  nock.disableNetConnect();
  // Enable only requests for the API under test
  nock.enableNetConnect("127.0.0.1");
});
// :37-52 — assert the OUTGOING payload, not just the response
nock("http://mailer.com").post("/send", (payload) => ((emailPayload = payload), true)).reply(202);
```

**Flow:** register interceptors for every collaborator → disable all other net connect → run the flow → assert both the response and (via captured payload) that the app called the collaborator with the right input. The "user does not exist" scenario (:14-27) shows simulating a 404 the real service would return.
**Invariant:** (1) isolation is fail-closed — unknown calls must throw, not silently pass. (2) mocking happens at the network layer, not by touching deployed code — "preferable… to act on the network level to keep the tests pure black-box" (:3). (3) compensate for isolation's blind spot (not detecting collaborator drift) with a few contract/E2E tests (:3).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'disableNetConnect\|enableNetConnect' sections/testingandquality/mock-external-services.md` = 2.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "disableNetConnect", "limit": 10}'
# resolves `sections/testingandquality/mock-external-services.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the intercept + fail-closed + payload-assert trio for any HTTP-isolation test. Adapt the mock library (nock vs Mock-Server vs wiremock). Omit nothing behavioral — fail-closed isolation is the load-bearing piece.
