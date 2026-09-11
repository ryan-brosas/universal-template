<!-- capsule-v2 -->
# Agent run status from event stream — why can't you trust the subprocess exit code?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you mark an agent run failed when the process exits 0 but the agent errored headlessly?

## Event-stream-derived status: `exitCode = errored || !agentEnded ? 1 : 0`
**Path/Symbol:** `packages/server/src/agent-runner.ts:runPi` (:103–305).
**Signature:** `runPi(request: AgentRunRequest): Promise<AgentRunResult>` via `runAgent` → harness dispatch (:532–536).
**Data Shape:** `AgentRunResult = { exitCode: number|null, findings: string|null (last assistant text or error), log: AgentLogEntry[]|string|null, changedFiles: string[] }`. Errored is set by FOUR independent signals: prompt-response `success:false` (:215), assistant message `stopReason==="error"`/errorMessage (:262), turn_end stopReason error (:279–281), and stream-close-before-agent_end (:201–204).

### Decisive source
```ts
const deadline = Date.now() + AUTOMATION_AGENT_RUN_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const line = await client.nextLine(Math.min(1000, deadline - Date.now()));
    if (line === null) {
      if (client.closed) {
        if (!agentEnded) errored = true;
        break;
      }
      continue;
    }
```
```ts
const exitCode = errored || !agentEnded ? 1 : 0;
```

**Flow:** resolve binary → spawn `pi --mode rpc` → optional set_model/set_thinking RPC commands (failure = immediate failed run with the error as log entry) → send prompt → bounded read loop classifying events → close client → derive findings/log/cap entries/diff git status → compute exitCode.
**Invariant:** The RPC event stream is the authority; a crash or timeout that never delivered `agent_end` yields exitCode 1 EVEN IF the OS process exited 0 — a headless API failure must surface as a failed automation run. Timeout expiry (10 min) without agent_end also fails the run. Model-selection failure aborts BEFORE prompting and synthesizes the failure as an assistant log entry.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`maps an error turn to a failed run with the error message as findings` :204–214 — FAKE_PI_ERROR emits stopReason "error" + errorMessage "Connection error."; result.exitCode===1, findings==="Connection error.").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "runPi agent_end errored stopReason", limit: 10 });
```

## Verdict
Adopt event-stream status derivation with the four-signal errored set and never trust process exit for harness-level failures; adapt timeouts/constants to your runner. Directly tested via a fake `pi --mode rpc` shell script (integration-tagged suite).
