<!-- capsule-v2 -->
# AAA test structure — what three phases make a test read declaratively, and what does a porter get wrong about Arrange scope?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How should every test be sectioned so the reader's brain parses intent without tracing imperative code?

## Arrange / Act / Assert with a 1-line Act and 1-line Assert
**Path/Symbol:** `sections/testingandquality/aaa.md` (explainer :3-5, good :9-21, anti-pattern :23-29).
**Signature:** test body layout only — no API. Arrange: all setup (construct SUT, add DB rows, stub/mock collaborators). Act: execute the unit under test, "usually 1 line". Assert: verify, "usually 1 line".
**Data Shape:** the anti-pattern (:23-29) shows the failure mode — a single bulk body with no phase separation, which "feels like reading imperative code (loops, inheritance)" instead of "like HTML — a declarative experience" (:3).

### Decisive source
```javascript
// aaa.md :9-21 — the canonical shape
test('When customer spent more than 500$, should be classified as premium', () => {
    //Arrange
    const customerToClassify = {spent:505, joined: new Date(), id:1}
    const DBStub = sinon.stub(dataAccess, 'getCustomer').reply({id:1, classification: 'regular'});
    //Act
    const receivedClassification = customerClassifier.classifyCustomer(customerToClassify);
    //Assert
    expect(receivedClassification).toMatch('premium');
});
```

**Flow:** read a test top-to-bottom as setup→trigger→verify. Uniform structure across the whole suite is the point — "once you get used to this pattern, you can read and understand the tests more easily… reduces the maintenance cost" (Unit Testing book quote :37). Related XUnit form: Setup/Exercise/Verify/Teardown.
**Invariant:** Act must be a single, obvious call; Assert a single, obvious expectation. If either needs loops or multiple calls, the test is testing too much. Assert-first is a legitimate authoring technique (Bill Wake quote :31) — write the expected outcome before the mechanics.
**Probe:** no runner upstream. Deterministic probe: `grep -c '//Arrange\|//Act\|//Assert' sections/testingandquality/aaa.md` = 3 (one each) in the good example.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "//Arrange", "limit": 10}'
# resolves `sections/testingandquality/aaa.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the three-phase layout as a universal test-authoring convention (any xUnit-style runner). Adapt comment style / phase names. Omit nothing behavioral — the phase discipline is the whole contract.
