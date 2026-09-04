<!-- capsule-v2 -->
# Airtable engine dual mode — how does the import engine swap live/mock transports, and why is its id map a module global?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do test and production Airtable fetch paths share one interface, and what does the static mapping table buy?

## Environment-selected transport + module-global mapTbl
**Path/Symbol:** `jobs/at-import/engine/index.ts:ATImportEngine` (whole, 122L) — `static get()` (:8-13), browser-clone headers on initialize/read/readView, `atBase` DEBUG_MOCK_AIRTABLE_IMPORT branch; `engine/mock.ts:ATMockImportEngine/MockAirtable` (whole); `helpers/syncMap.ts` (whole, 31L).
**Signature:** `ATImportEngine.get() → isPlayWrightNode() ? new ATMockImportEngine() : new ATImportEngine()`; methods `initialize({appId, shareId})`, `read({link, cookie, headers})`, `readView(viewId, {cookie, headers, baseInfo})`, `atBase({apiKey, baseId})`.
**Data Shape:** read/readView return axios responses with `responseType: 'stream'`; readView URL carries `stringifiedObjectParams` + `accessPolicy` (shareId/applicationId/signature/expires) JSON-encoded as query params.

### Decisive source
```ts
export class ATImportEngine extends ATMockImportEngine {
  static get() {
    if (isPlayWrightNode()) { return new ATMockImportEngine(); }
    return new ATImportEngine();
  }
  atBase({ apiKey, baseId }) {
    if (process.env.DEBUG_MOCK_AIRTABLE_IMPORT === 'true') {
      return ((title) => new MockAirtable(title)) as any as AirtableBase;
    }
    return new Airtable({ apiKey }).base(baseId);
  }
}
// syncMap.ts — module scope, NOT per-run state:
export const mapTbl = {};
export const addToMappingTbl = (aTblId, ncId, ncName, parent?) => { mapTbl[aTblId] = { ncId, ncParent: parent, ncName }; };
```

**Flow:** the factory picks the mock engine whenever running inside Playwright (e2e tests), and `atBase` can be forced to mocks independently via env — both implement the identical four-method surface, so `at-import.processor.ts` never knows which it holds. Live reads replay a full Chrome header set against airtable.com share links, streaming responses straight into the parser layer; view reads sign every request with the accessPolicy captured at initialize. During schema/data phases, `addToMappingTbl` records airtable-id → ncId (+parent, +name for debug) so later link phases resolve forward references by lookup.
**Invariant:** extending ATMockImportEngine means the LIVE class inherits mock bodies as documentation-of-shape — any method the live class omits silently falls back to fake data, which is exactly what makes e2e safe but makes "did I override this?" load-bearing. The global mapTbl is single-run-by-convention (one active import per instance); persisting or sharing it across concurrent imports would cross-wire ids. MockAirtable.eachPage must keep the cursor-in-closure paging contract (`fetchNextPage` advances) or processors hang.
**Probe:** no unit test upstream; e2e usage via Playwright detection is the integration probe. Source-grounded probe: inheritance `extends ATMockImportEngine` with only initialize/read/readView/atBase overridden; DEBUG env branch returns the mock cast AS the real AirtableBase type.
**Coverage caveat:** no in-repo unit tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ATImportEngine ATMockImportEngine MockAirtable eachPage addToMappingTbl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the twin-engine same-interface swap for any third-party importer needing deterministic tests; adapt the selection signal; replace the module-global map with an injected store if you allow concurrent imports.
