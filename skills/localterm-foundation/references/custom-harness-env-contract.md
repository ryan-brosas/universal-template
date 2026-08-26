<!-- capsule-v2 -->
# Custom harness env-var contract — how do you hand an arbitrary shell command an agent prompt safely?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Why is the prompt delivered as an environment variable instead of argv?

## LOCALTERM_AGENT_* envelope over a shell-spawned subprocess
**Path/Symbol:** `packages/server/src/agent-runner.ts:runCustom` (:377–468).
**Signature:** `(request: AgentRunRequest, config: CustomHarnessConfig): Promise<AgentRunResult>`.
**Data Shape:** Env vars: `LOCALTERM_AGENT_PROMPT` (the prompt itself), `_SESSION_MODE`, `_SESSION_FILE` ("" when fresh), `_MODEL`, `_THINKING` ("" when unset); capture caps both streams at `AUTOMATION_CUSTOM_HARNESS_CAPTURE_BYTES = 65536`.

### Decisive source
```ts
const child = spawn(config.command, {
      cwd: request.cwd,
      env,
      shell: true,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    }) as ChildProcess;
```

**Flow:** snapshot git status → mkdir session parent → build env (process.env + request.env secrets + LOCALTERM_AGENT_*) → spawn via shell → bounded-capture stdout/stderr → timeout SIGTERM then SIGKILL after `AUTOMATION_AGENT_FORCE_KILL_DELAY_MS = 3_000` → on close: killed-or-signalled ⇒ exitCode null, else code; findings = stdout (fallback stderr) truncated to 8k; log = stdout + `\n--- stderr ---\n` + stderr capped at 64k.
**Invariant:** The prompt rides in ENV, never argv, because commands run through `shell:true` — a prompt containing quotes/`;`/$() would execute or corrupt the command line if interpolated into argv; env values need no escaping. A signal death or force-kill maps to exitCode **null** (not 1) so "timed out" stays distinguishable from "command failed"; spawn errors are caught and converted to a failed result with a stderr note instead of rejecting.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`runs the custom command with the prompt in env and captures stdout as findings` :286–301 — asserts `findings === "out: do thing"` proving the env round-trip; `marks a non-zero custom command exit as failed` :322 pins exitCode passthrough).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "runCustom LOCALTERM_AGENT_PROMPT custom harness", limit: 10 });
```

## Verdict
Adopt env-carried prompt + bounded dual-stream capture + TERM-then-KILL escalation with null-on-signal; adapt var names/caps to host. Directly tested including the 2× cap overflow case (:303).
