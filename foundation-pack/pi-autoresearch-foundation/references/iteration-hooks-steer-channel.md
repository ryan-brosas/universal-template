<!-- capsule-v2 -->
# Before/after iteration hooks — how can an external process steer a running experiment loop?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the hook contract (discovery, stdin, stdout), and how is hook output kept from hijacking the loop?

## runHook + steerMessageFor — executable-only scripts, JSON on stdin, 8KB-capped stdout as steer text
**Path/Symbol:** `harness/hooks.ts` — constants :17–26 (`TIMEOUT_MS=30_000`, `STDOUT_MAX_BYTES=8*1024`, `TRUNCATION_MARKER`), runner :109–161, steer mapping :167–179, gated log-append :192–224; fire sites `harness/server.ts:925–935` (before) + :1431–1442 (after).
**Signature:** script path `<workDir>/autoresearch.hooks/{before,after}.sh`; payload JSON piped to stdin: before `{event:'before', cwd, next_run, last_run, session}` / after `{event:'after', cwd, run_entry, session}`; SessionSnapshot `{metric_name, metric_unit, direction, baseline_metric, best_metric, run_count, goal}`.
**Data Shape:** HookResult `{fired, stdout, stderr, exitCode, timedOut, durationMs}`.

### Decisive source
```ts
child.stdout.on('data', (chunk: Buffer) => {
  if (stdoutFull) return;
  const remaining = STDOUT_MAX_BYTES - stdoutBytes;
  if (chunk.length <= remaining) { /* accumulate */ return; }
  const kept = truncateAtBoundary(chunk.subarray(0, remaining)); // last newline, else UTF-8-safe char trim
  stdout += kept.toString('utf8') + TRUNCATION_MARKER;
  stdoutFull = true;                                             // hard one-shot cap at 8KB
});
```

**Flow:** run/log → `fireHook` → skip silently when script missing or not X_OK-executable regular file → spawn with 30s timeout → write payload JSON to stdin and end → collect bounded stdout + unbounded stderr → map to steer text: timeout ⇒ `[before hook timed out after 30s]`; nonzero exit ⇒ bracketed exit code + stderr+stdout (an ERROR becomes visible steering); success ⇒ trimmed stdout becomes the steer message prefixed into the agent-visible response (`🪝 before-hook: …`). Every fired hook appends `{type:'hook', stage, exit_code, duration_ms, stdout_bytes, timed_out}` to the JSONL — but ONLY if the file already has a config header.
**Invariant:** hooks can ADVISE (inject text) but never BLOCK or mutate state directly — there is no channel from hook output to keep/discard decisions. The UTF-8-boundary truncation prevents a multibyte character straddling the cap from becoming replacement garbage mid-message. The hasConfigHeader gate keeps stray hook executions from seeding a malformed ledger in directories that aren't real sessions.
**Probe:** anchors: `grep -nE 'STDOUT_MAX_BYTES|TRUNCATION_MARKER' harness/hooks.ts | cut -d: -f1` → :18, :19 (consts), :128, :135 (cap logic); `grep -n 'hasConfigHeader' harness/hooks.ts` → :193 def + :216 gate; direct tests `__tests__/unit/state.test.ts` describe('Session lifecycle cleanup') covers watcher cleanup semantics around hooks-adjacent teardown.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "runHook steerMessageFor autoresearch.hooks appendHookLogEntryIfConfigured", limit: 10 });
```

## Verdict
Adopt the advise-only hook contract, exec-gate, stdin-JSON protocol, and header-gated logging verbatim; adapt script discovery/timeout to host; omit the UTF-8 boundary walk only for single-byte locales. Coverage caveat: hooks module has no dedicated vitest — source-pinned.
