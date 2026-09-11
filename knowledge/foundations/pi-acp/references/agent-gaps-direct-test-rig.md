<!-- capsule-v2 -->
# Agent-gap direct tests — how do you test ACP agent methods (fork/resume/close/usage) with zero real subprocesses, and what fork behaviors do those tests pin?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you direct-test the agent's unstable session methods and the PromptResponse.usage attachment without spawning pi — and which fork behaviors are pinned by tests rather than prose?

## test/unit/agent-gaps.test.ts — the subprocess-free agent test rig
**Path/Symbol:** `test/unit/agent-gaps.test.ts` (whole, 307L, 7 tests) + `test/helpers/fakes.ts` (`FakeAgentSideConnection`, `asAgentConn`).
**Signature:** `buildAgent(opts: { conn?, stored?, proc?, sessions? }): { agent: PiAcpAgent; conn: FakeAgentSideConnection }` — swaps `(agent as any).sessions` / `(agent as any).store` for plain-object doubles and monkey-patches `PiRpcProcess.spawn` (original saved, restored in `finally`).
**Data Shape:** fake sessions expose `maybeGet/getOrCreate/create/closeSession/closeAllExcept`; fake store exposes `get/upsert/delete`; fake procs return canned `getEntries` (`{entries, leafId}`), `fork(entryId) → {text, cancelled}`, `getState`, `getAvailableModels`, `getSessionStats`.

### Decisive source
```ts
const originalSpawn = PiRpcProcess.spawn
;(PiRpcProcess as unknown as Record<string, unknown>).spawn = async (params) => {
  spawned.push(params)
  return { onEvent: () => () => {},
    getEntries: async () => ({ entries: [u1, a1, u2], leafId: 'u2' }),
    fork: async (entryId) => { forkCalls.push(entryId); return { text: 'Forked', cancelled: false } },
    getState: async () => ({ sessionId: 'forked-pi-id', sessionFile: '/tmp/…/branched.jsonl' }),
    getAvailableModels: async () => ({ models: [{ provider: 'openai', id: 'gpt-4o' }] }) }
}
try { /* …run the ACP method… */ } finally { PiRpcProcess.spawn = originalSpawn }
```

**Flow:** fork test pins the full contract: spawn params carry `cwd` + the SOURCE `sessionPath`; `forkCalls === ['u2']` (the LAST user-message entry — reverse-find `type==='message' && role==='user'`); the new ACP session adopts pi's fresh id; `store.upsert` receives EXACTLY `{sessionId, cwd, sessionFile}`; `_meta.piAcp.fork` deep-equals `{fromSessionId, entryId, text, cancelled, sessionFile}`; `closeAllExcept('forked-pi-id')` enforces single-live-subprocess. Failure tests: empty entries → dispose + reject `/no user messages to fork from/` with `disposed === ['proc']`; unknown sessionId → reject with `data === 'Unknown sessionId: nope'`; relative cwd → `data === 'cwd must be an absolute path: relative'` — both BEFORE any spawn. resume test pins spawn-with-stored-sessionPath + `configOptions`/`modes` in the response. closeSession test pins cancel-then-remove for a live id and a silent no-op for unknown ids. Usage test pins `res.usage` deep-equals `{totalTokens: 15, inputTokens: 10, outputTokens: 5, _meta: {piAcp: {cost: 0.5}}}` from a canned `getSessionStats`.
**Invariant:** the ACP method layer is fully testable against a fake connection + doubles — no test needs a real pi process; every spawn monkey-patch is restored in `finally` so suites stay order-independent; validation errors reject BEFORE resource creation (no bridge/subprocess leak on bad input).
**Probe:** `node --import tsx --test test/unit/agent-gaps.test.ts` (7 tests: initialize capabilities, fork happy path, fork empty-source cleanup, fork validation rejects, resume restore, resume unknown-id, closeSession live/unknown, prompt usage attachment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "unstable_forkSession resumeSession closeSession usage agent-gaps FakeAgentSideConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-and-monkey-patch rig for testing an ACP agent's method surface without subprocesses (swap manager/store, patch the spawn static, restore in finally), and the validate-before-spawn error contract. Adapt the fake shapes to your SDK's connection interface. Omit the deep-equality `_meta` pins unless your protocol carries the same extension envelope. Coverage caveat: this suite had ZERO prior leaf citations — it is the only direct test for fork/resume/close/usage at this pin.
