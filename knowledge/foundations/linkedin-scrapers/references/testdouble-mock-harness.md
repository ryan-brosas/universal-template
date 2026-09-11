<!-- capsule-v2 -->
# Testdouble axios mock harness — module-replacement fixtures that pin wire format end-to-end (how do I test an API client without a recorder or a live session)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** How does this repo get high-confidence tests of cookie auth + envelope parsing with zero network, and what's the reusable fixture architecture?

## The harness
**Path/Symbol:** `test/utils/mockAxios.ts` + `test/utils/defaultMocks.ts` + `test/utils/mockLogin.ts`; consumers e.g. `test/search/search-repository.spec.ts:1–20`.
**Signature:** `defaultMocks(): Promise<{Client, axios}>` — `replace('fs/promises')` (testdouble MODULE replacement), replace axios instance methods, `mockLogin(axios)`, THEN dynamic-`import('../../src/core/client')`.
**Data Shape:** stubs keyed by EXACT URL (built with `new URL(path, linkedinApiUrl).toString()`) and often exact `{params}` dicts; responses are minimal `{data: response}` envelopes built by per-domain factories (`search-factories.creatSearchPeopleResponse(n)` etc.).

### Decisive source
```ts
export const defaultMocks = async () => {
  replace('fs/promises');                       // sessions.json never touches disk
  const { axios } = mockAxios();                // replace the axios instance
  mockLogin(axios);                             // seed-JSESSIONID + authenticate POST stubs
  const { Client } = await import('../../src/core/client');   // import AFTER replacement
  return { Client, axios };
};
// per-test wiring:
when(axios.get(requestUrl, { params: matchers.contains({ start: 0, count: 10 }) })).thenResolve({ data: searchResults });
when(axios.get(url, { params: {...reqParams, createdBefore: page[9].createdAt} }), { times: 2 }).thenResolve({ data: secondPageResponse });
verify(axios.get(), { ignoreExtraArgs: true, times: 0 });     // cache-hit ⇒ ZERO calls
```

**Flow:** replace modules → dynamic-import client (so it binds the doubles) → stub per-URL+params with ordered/timed expectations → drive PUBLIC API (`client.search.searchPeople().scrollNext()`) → assert on parsed OUTPUT shapes (key sets, joins, ordering), not internals. Sequence-dependent pagination is stubbed per-cursor (`createdBefore: firstPage[9].createdAt`, `{times: 2}` for repeat fetches).
**Invariant:** import ORDER is load-bearing (replacements must precede the first import of the module under test); URL builders in tests mirror `config.linkedinApiUrl` so a base change breaks loudly. Factories emit VALID `$type`-tagged included[] rows, which is what makes envelope-parsing tests meaningful — garbage-in fixtures would prove nothing.
**Probe:** the suite itself: `login.spec.ts` pins header merge/cache branches; `search-repository.spec.ts` pins paging math + filter rewrites; `message-repository.spec.ts:200–259` pins scrollBack LIFO semantics; run via `yarn jest` (jest.config.js roots at `test/`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "mockAxios defaultMocks", limit: 10, fields: ["signature", "name", "file"], include_tests: true });
```

## Verdict
Adopt the replace→import→stub-by-wire-shape→assert-parsed-output ladder for ANY scraper/API-client repo lacking a live-session CI. Adapt to your mock lib (msw/testdouble). Omit the deprecated `faker.datatype` calls (upstream rot). This suite is the direct-test backbone that lets every other capsule in this foundation claim test-pinned probes.
