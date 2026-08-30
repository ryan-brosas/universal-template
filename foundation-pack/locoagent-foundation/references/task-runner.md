<!-- capsule-v2 -->
# Scheduled task runner — how does a cron-style entry point compose workflow pre-runs, dedup state, and a task file into one agent session?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you wire deterministic pre-session work and cross-session memory into a single prompt-driven agent run that stays within a hard time budget?

## Pre-run workflows → assemble prompt → `--print` the agent
**Path/Symbol:** `scripts/run-tasks.ts`:`runDueWorkflows` (`:58-102`), prompt assembly (`:106-154`), agent spawn (`:169-183`).
**Signature:** CLI: `run-tasks.ts [--dry-run] [--platform <p>]`; `spawnSync('bun', ['run', '--preload', GLOBALS, CLI_ENTRY, '--print', prompt], { timeout: 30 * 60 * 1000 })`.
**Data Shape:** Workflow list rows from engine `list`: `{ id, name, schedule, status, lastRun, lastResult }`; daily-only selection with skip reasons rendered into the prompt as `- <name>: skipped (status=running|already ran today)`.

### Decisive source
```ts
// Skip non-daily or already running/stopped
if (wf.schedule !== 'daily') continue
if (wf.status === 'running' || wf.status === 'stopped') {
  results.push(`- ${wf.name}: skipped (status=${wf.status})`); continue
}
// Skip if already ran today (ISO-date prefix compare on lastRun)
const today = new Date().toISOString().split('T')[0]!
if (wf.lastRun !== 'never' && wf.lastRun.startsWith(today)) {
  results.push(`- ${wf.name}: skipped (already ran today)`); continue
}
```
and the rules block every session gets:
```
- ALWAYS run `log-operation.ts check ...` before each action
- ALWAYS run `log-operation.ts add ... --status success` after each successful action
- If a post URL is already in the operation log for that action, skip it silently
At the end, run `log-operation.ts recent --limit 20` and report what was completed/skipped/errored.
```

**Flow:** load `persona/tasks.md` → fetch the op-log 7-day summary (failure ⇒ "(operation log unavailable)" placeholder, never abort) → run due DAILY workflows synchronously before the agent wakes (10 min timeout each; already-ran-today is an ISO date-prefix check on `lastRun`) → build one big prompt: weekday context (Monday ⇒ also weekly tasks) + tasks + workflow results + log summary + ordered instructions → `--dry-run` prints it instead of executing → otherwise launch the CLI in print-mode with a 30-minute cap.
**Invariant:** The whole day is ONE bounded headless session (`--print`, 30 min): deterministic work runs BEFORE the LLM so tokens are spent only on judgment; every rule the agent must follow is restated inside the prompt itself (never assumed); failures of auxiliary state (log summary) degrade to placeholders rather than killing the session.
**Probe:** No direct test for run-tasks (coverage caveat — source-grounded). Deterministic probe: grep pins `schedule !== 'daily'` at `scripts/run-tasks.ts:72` and the 30-min timeout at `:176`; `--dry-run` output is directly inspectable without Bun-side effects.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runDueWorkflows dry run tasks prompt", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt pre-session deterministic workflow draining, once-per-day idempotence via ISO-date prefix, soft-degrading state fetches, and full rule restatement inside the composed prompt. Adapt schedules, persona files, and CLI entry. Omit the specific social-media instruction content — the composition pattern is the portable contract.
