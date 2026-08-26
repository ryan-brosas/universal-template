<!-- capsule-v2 -->
# 3-part test names — what three clauses make a failing test self-explanatory to QA and future-you?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you name a test so the report reads like a requirements document without reading the code?

## unit-under-test / circumstance / expected-result
**Path/Symbol:** `sections/testingandquality/3-parts-in-name.md` (explainer :3, good :7-17, anti-pattern :19-27).
**Signature:** `describe('Products Service')` → `describe('Add new product')` → `it('When no price is specified, then the product status is pending approval')`. The `it` clause carries parts 2+3; the describe stack carries part 1.
**Data Shape:** three parts: (1) what is being tested (`ProductsService.addNewProduct`), (2) under what scenario (`no price passed`), (3) expected result (`product not approved`). Anti-pattern `it('Should return the right status')` forces reading the whole body to recover intent (:19-27).

### Decisive source
```javascript
// 3-parts-in-name.md :7-17
describe('Products Service', () => {
  describe('Add new product', () => {
    it('When no price is specified, then the product status is pending approval', () => {
      const newProduct = new ProductService().add(...);
      expect(newProduct.status).to.equal('pendingApproval');
    });
  });
});
```

**Flow:** test report should answer "does this revision satisfy requirements" for non-code readers (tester, DevOps, future-you) (:3). Naming at the requirements level makes a failed "Add product" test say exactly what malfunctioned.
**Invariant:** the name alone must state scenario + expectation; the body is confirmatory, not the source of truth. If a reader must open the test to understand intent, the name is wrong.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'When no price is specified' sections/testingandquality/3-parts-in-name.md` = 1; anti-pattern 'Should return the right status' present.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "When no price is specified", "limit": 10}'
# resolves `sections/testingandquality/3-parts-in-name.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the three-clause naming contract for any test suite. Adapt phrasing conventions per team. Omit nothing — naming is a zero-cost high-leverage invariant.
