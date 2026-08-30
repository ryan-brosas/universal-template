<!-- capsule-v2 -->
# Detached process group timeout — how does a hung benchmark get killed without orphaning children?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What spawn flags make whole-tree kill work on both POSIX and Windows, and how does the timeout surface in results?

## spawn detached:true + killProcessTree(-pid) — SIGTERM the group, taskkill fallback
**Path/Symbol:** `harness/server.ts` — spawn :978–983; timeout timer :1028–1034; `killProcessTree` :280–296; result fields `killed`→`timedOut`.
**Signature:** `spawn(bash, ['-c', command], { cwd: workDir, detached: true, stdio: ['ignore','pipe','pipe'], windowsHide: true })`; `killProcessTree(pid)` → POSIX `process.kill(-pid,'SIGTERM')` falling back to `process.kill(pid)`; win32 `taskkill.exe /pid <pid> /t /f`.
**Data Shape:** resolved promise `{ exitCode, killed, output, tempFilePath?, actualTotalBytes }`; `benchmarkPassed = exitCode === 0 && !timedOut`.

### Decisive source
```ts
timeoutHandle = setTimeout(() => {
  processTimedOut = true;
  if (child.pid) killProcessTree(child.pid);
}, timeout);
// ...
child.on('close', (code) => { /* resolve({ exitCode: code, killed: processTimedOut, ... }) */ });
```

**Flow:** run action → bash -c spawned DETACHED (own process group leader on POSIX) → on timeout the negative-PID signal hits the entire group (children included); ENOENT-style group kill falls back to direct pid kill; Windows route uses taskkill's `/t` tree flag. Timeout ⇒ `killed=true` ⇒ response leads with `⏰ TIMEOUT after Xs` and `benchmarkPassed=false` REGARDLESS of exit code — a timed-out run that exits 0 during teardown still counts as failed. `session.runningExperiment` cleared in `.finally()` (:1061–1063) so widget state survives abnormal exits.
**Invariant:** detached:true is load-bearing for group kill — without it `-pid` targets nothing and grandchildren survive as orphans holding the terminal/ports. `!timedOut` participates in pass computation independently of exit code (a "successful" timeout must not be loggable as a keep-worthy benchmark). stdio stdin 'ignore' prevents the child from waiting on input forever.
**Probe:** anchors: `grep -n 'detached: true' harness/server.ts` → :980 (run) — hooks.ts spawn deliberately NOT detached (30s-bounded hook); `grep -n 'killProcessTree' harness/server.ts` → :280 def + :1032 call; `grep -n "process.kill(-pid" harness/server.ts` → :290.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "killProcessTree detached processTimedOut taskkill", limit: 10 });
```

## Verdict
Adopt detached+group-kill+timedOut-overrides-exit-code verbatim (this trio is what makes unattended autonomous loops safe against runaway benchmarks); adapt signal choices/limits; omit the Git-Bash resolution twin (`platform.ts resolveBashPath`) unless porting to Windows. No direct test drives the timeout path — source-pinned.
