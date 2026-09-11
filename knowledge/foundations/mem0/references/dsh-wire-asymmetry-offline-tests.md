<!-- capsule-v2 -->
# dsh-mem0 endpoint asymmetry + offline test harness — where does scope ride on the wire, and how is this tested with no network?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** Why does search put entity params inside `filters` while add takes them top-level, and how do the tests exercise both tools without any Mem0 dependency?

## Two-endpoint contract + vi.mock harness
**Path/Symbol:** `integrations/dsh-mem0/src/index.ts` (`client.search(query, { filters, topK })` :104; `client.add([{role,content}], {…addParams, source})` :127-130) with `integrations/dsh-mem0/tests/apply.test.ts` mock scaffold :4-35.
**Signature:** `search(query: string, opts: { filters: Record<string,string>; topK?: number })` vs `add(messages: [{ role: "user"; content: string }], opts: { userId?, agentId?, runId?, source? })`.
**Data Shape:** `DEFAULT_SEARCH_LIMIT = 10`; `topK = limit && limit > 0 ? limit : 10` (zero/negative fall back); write payload is a single user-role message plus camelCase params and `source = "DEEPSEEK_HARNESS"`.

### Decisive source
```ts
// Recall. The platform rejects top-level entity params on search, so scope
// goes inside `filters` (unlike add below, which takes them top-level).
const { results } = await client.search(query, { filters, topK });
...
const result = await client.add([{ role: "user", content: text }],
                                { ...addParams, source: SOURCE });
```
```ts
vi.mock("mem0ai", () => ({ MemoryClient: class { search = mockSearch; add = mockAdd; } }));
vi.mock("@deepseek-ai/dsh-tools", () => ({ defineTool: (options) => options }));
function applyAndCollect(config) {
  const tools = new Map();
  apply({ tools: { register: (t) => tools.set(t.name, t) } } as never, config);
  return tools;
}
```

**Flow:** search → resolve snake filters → `client.search(query, {filters, topK})` → format+truncate. add → resolve camel params → `client.add([user message], {…params, source})`. Tests: swap both peer modules with mocks → call `apply` with a fake ctx that collects registrations by name → invoke `execute(args)` directly and assert on returned strings AND on exact wire calls (`toHaveBeenCalledWith("drink", { filters: { user_id: "u" }, topK: 10 })`, `{ userId: "u", source: "DEEPSEEK_HARNESS" }`).
**Invariant:** The platform REJECTS top-level entity params on search — filters-only there is not style, it's the API surface; add is the mirror image (top-level through the SDK converter). The in-source comment is the porting warning: keep each param class at ITS endpoint or the call fails server-side. The test harness proves the whole plugin runs OFFLINE: mocking only the two peers leaves real production code under test, and assertions pin exact wire shapes (scope placement, casing, default topK=10, source tag).
**Probe:** `cd integrations/dsh-mem0 && vitest run` → **29/29 GREEN at pin `7e09615` via vitest v4.1.10 (executed live this pass)**; per-test anchors: "honors a per-call userId override and limit" (:83-93), "reports the write as queued…with camelCase scope + source" (:107-122), env-var save/restore guards (:37-48).
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `applyAndCollect vi.mock MemoryClient` limit 3 → `integrations.dsh-mem0.tests.apply.test.applyAndCollect` apply.test.ts 28-35 rank 1 line-exact.

## Verdict
Adopt the endpoint split (search=filters+topK, add=top-level camel+source) as THE wire contract, the `limit>0` guard, and the two-mock offline test recipe for ANY harness plugin over a network SDK. Adapt tool names/copy to your host. Omit real-network integration tests — this suite deliberately has none.
