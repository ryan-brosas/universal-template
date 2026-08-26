<!-- capsule-v2 -->
# In-process tool harness — how do you exercise a registered tool's full execute() path without spawning the agent CLI?

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** Once an extension registers its tools through the host's `registerTool` callback, how can tests invoke those tools end-to-end (real registration → real execute → real files) while skipping the expensive CLI/model layer?

## In-process tool harness
**Path/Symbol:** `test/e2e.ts` — `registeredTools()` (:61–76), `registeredToolNames()` (:78–80), `toolExecutionContext()` (:82–92), `runTool()` (:94–99), `toolResultText()` (:101–103). Contrast plane: `runPi()` (:106+) spawns the real CLI and is covered by `live-cli-eval-isolation.md`.
**Signature:** `registeredTools(): Record<string, any>`; `runTool(name: string, params: Record<string, unknown>): Promise<any>`; `toolResultText(result: any): string`.
**Data Shape:** the mock `pi` object implements only `registerTool(tool)` (captures by `tool.name` when it is a string) and `on(event, handler)` (deliberately ignored — hooks are irrelevant for direct execution). Tool context = `{ sessionManager: { getSessionId: () => sessionId }, hasUI: false, ui: { notify() {} } }`; default session id `"e2e-test"`.

### Decisive source
```ts
// registeredTools (61-76): REAL extension, MINIMAL host — load index.ts in-process
const pi = {
	registerTool(tool: { name?: unknown }) {
		if (typeof tool.name === "string") tools[tool.name] = tool;
	},
	on(_event: string, _handler: unknown) { /* hooks irrelevant here */ },
};
registerExtension(pi as any);
return tools;

// runTool (94-99): assert registration, then drive the production execute()
async function runTool(name: string, params: Record<string, unknown>) {
	const tools = registeredTools();
	const tool = tools[name];
	assert(Boolean(tool), `${name} tool is not registered`);
	return await tool.execute(`e2e-${name}`, params, null, null, toolExecutionContext());
}

// toolResultText (101-103): flatten the content-part envelope to comparable text
return (result.content ?? []).map((part) => (part.type === "text" ? part.text : "")).join("\n");
```

**Flow:** (1) `registeredTools()` imports the actual `registerExtension` from `../index.js` and replays registration against a two-method fake host; the returned map IS the live registry. (2) `runTool` asserts the tool exists, then calls its production `execute(toolCallId, params, null signal, null onUpdate, ctx)` — the same function the real agent runtime dispatches. (3) Mutating scenarios (`testMemoryWriteAndRecall`, `testScratchpadCycle`, `testDailyLog`) run against the developer's real memory dir inside the backup/restore envelope from `main()`. (4) Assertions read results via `toolResultText` and/or the files on disk. (5) `registeredToolNames()` powers the load check (`testExtensionLoads` expects the sorted name list).

**Invariant:** the harness must exercise the UNMODIFIED production module — no re-implemented tool logic; hook subscriptions may be dropped but every registered tool must be capturable; missing tools fail loudly ("tool is not registered") instead of returning undefined.

**Probe:** EXECUTED pass 4 indirectly via the unit suite's own mock-`pi` pattern (`createMockPi`, cited in test-harness.md); direct e2e tier requires `pi` on PATH + API key (runner block recorded in verification.md). Deterministic content checks: `grep -c "runTool" test/e2e.ts` = 1 definition + 8 scenario call sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "runTool toolExecutionContext registeredTools toolResultText", limit: 10, fields: ["signature", "name", "file"] });
```
Pass-4 retrieval: `get_code_snippet(pi-memory.test.e2e.runTool)` / `(pi-memory.test.e2e.toolExecutionContext)` returned the excerpts above; inbound trace shows 8 scenario callers; `check_index_coverage(test/e2e.ts)` = `no_recorded_issue`.

## Verdict
Adopt the minimal-two-method host + real-extension-registration replay and the direct `execute()` invocation pattern whenever a ported extension exposes a registry surface; adopt the strict registration assertion and content-part flattening helper. Adapt the context shape (`sessionManager`/`ui`) to the host's tool-context contract. Omit nothing — this harness is pure test infrastructure. Pair it with `live-cli-eval-isolation.md`: use this for tool semantics, escalate to the real CLI only for injection/model-observable behavior.
