<!-- capsule-v2 -->
# Subagent liveness gate — why does the supervisor wait for child pi processes before judging?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How are child subagents detected extension-agnostically, and what does the supervisor do on timeout?

## checkChildPiProcesses + waitForSubagents (`src/subagent-detector.ts`)
**Path/Symbol:** `src/subagent-detector.ts:checkChildPiProcesses` (:24-68), `waitForSubagents` (:74-90).
**Signature:** `checkChildPiProcesses(): Promise<SubagentStatus>` (`{hasActiveSubagents, count, pids}`); `waitForSubagents(checkIntervalMs=2000, timeoutMs=60000): Promise<{completed, finalStatus}>`.
**Data Shape:** `ps -eo ppid,pid,comm` parsed as `ppid pid command`; a subagent = row with `childPpid === process.pid && comm === 'pi'`.

### Decisive source
```ts
const { stdout } = await execAsync(`ps -eo ppid,pid,comm | grep -E "\\bpi\\b" || true`);
...
if (childPpid === ppid && comm === 'pi') pids.push(childPid);
// direct children ONLY in the parse — but comment notes grandchildren surface
// because subagents spawn their own `pi` children under our child's pid... (see invariant)
// Windows: not implemented — assume no subagents (fail-open)
```

**Flow:** `agent_settled` fires → check status → if active: widget shows "Waiting for N subagent(s)" → poll every 2s up to 120s (index.ts :248 overrides the 60s default) → still running at timeout ⇒ WARNING notification then PROCEED WITH ANALYSIS anyway ("Supervisor: N subagent(s) still running after timeout, proceeding").
**Invariant:** (1) Detection is deliberately mechanism-blind: it doesn't care HOW subagents were made (pi-messenger, manual spawn) — only that child processes named `pi` exist. (2) Fail-open everywhere: exec errors, empty ps output, malformed lines, and Windows ALL report "no subagents" — supervision never blocks on its own detection failing. (3) Timeout also fails-open but LOUDLY (warning), because judging while children run is imperfect yet better than never judging. (4) The gate runs BEFORE ineffective-pattern detection so waiting children don't count as stagnation.
**Probe:** `tests/subagent-detector.test.ts` — `detects child pi processes` (:35), `ignores non-pi processes` (:58), `ignores pi processes from other parents` (:78), `handles exec errors gracefully` (:97), `times out if subagents don't complete` (:170).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "checkChildPiProcesses waitForSubagents ppid comm", limit: 8 });
```

## Verdict
Adopt fail-open child-liveness gating before any settled judgment. Adapt the process name/pattern to your agent binary. Omit entirely if your host cannot spawn nested agents.
