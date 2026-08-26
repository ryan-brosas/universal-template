<!-- capsule-v2 -->
# Live benchmark dashboard — TTY render loop, signal forwarding, and alt-screen lifecycle

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** While a benchmark executor runs as a child process, how do you render a live progress dashboard that survives Ctrl+C (forwarding it to the child), works without a TTY, and always restores the terminal?

## Poll-render loop + SIGINT-as-forward + finally-block restoration
**Path/Symbol:** `packages/metaharness/src/runner.ts` — `runBenchmark` monitor section (1636-1708), `render` (868-918), status-sorted trial table (893-906), formatters `fmtUsd/fmtNum/fmtDur/bar` (454-480).
**Signature:** loop: `while (!finished) { render(st); await Bun.sleep(isTTY ? 700 : 10000); } render(st);` with `proc.exited.then(code => { exitCode = code; finished = true; })`.
**Data Shape:** frame = header (dataset · agent · models · conc/k) + progress bar + pass/fail/err/run/pend counts + spend/tokens + trial rows sorted running→error→fail→pass then name; non-TTY emits one `[harbor] done/total pass=…(x%) …` line per tick.

### Decisive source
```ts
const onSig = (): void => {
    try { proc.kill("SIGINT"); } catch { /* ignore */ }
};
process.on("SIGINT", onSig);
process.on("SIGTERM", onSig);
try {
    while (!finished) { render(st); st.tick++; await Bun.sleep(isTTY ? 700 : 10000); }
    render(st); // final frame
} finally {
    gatewayForward?.stop();
    if (isTTY) process.stdout.write(`${ESC}?25h${ESC}?1049l`); // restore cursor + screen
    try { fs.closeSync(logFd); } catch {}
    process.off("SIGINT", onSig); process.off("SIGTERM", onSig);
}
```
```ts
// table: running first, then errors/fails, then passes; recent first within
const order: Record<TrialStatus, number> = { running: 0, error: 1, fail: 2, pass: 3 };
const sorted = [...trials].sort((a, b) => order[a.status] - order[b.status] || a.name.localeCompare(b.name));
const maxRows = isTTY ? Math.max(6, (process.stdout.rows ?? 40) - rows.length - 4) : sorted.length;
```

**Flow:** spawn the executor with stdout/stderr redirected to a log file (the monitor owns the terminal) → enter the render loop: read all trials from disk each tick (running trials get live cost via the probe capsule), aggregate, draw the frame — viewport-height-aware row cap when TTY, plain lines otherwise → SIGINT/SIGTERM handlers do NOT die: they forward the signal to the child so the child's own graceful shutdown runs, and the loop keeps rendering until the child exits → after exit: final frame, restore screen/cursor, close log fd, remove handlers (all in `finally`, so an exception can't strand alt-screen mode), then write the summary and report.
**Invariant:** Ctrl+C means "stop the CHILD", not "kill the monitor mid-write" — the monitor must stay alive long enough to flush final state and restore the terminal; every terminal-mode mutation has its inverse in a `finally`; render cadence adapts to interactivity (700ms TTY vs 10s piped); the trial table surfaces actionable rows (running/errors) first under any viewport height.
**Probe:** no automated test drives the TTY loop (interactive-only surface) — coverage caveat recorded. The deterministic pieces it composes ARE pinned: totals aggregation via manager.test.ts fixtures, cost probing via `test/runner.test.ts:145-180`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runBenchmark render SIGINT proc.exited Bun.sleep alt screen", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape for any CLI wrapper around a long child process: signal-forward-not-die, poll-from-disk rendering, adaptive cadence, priority-sorted tables, total `finally` restoration. Adapt intervals, frame layout, and ANSI handling to your UI; omit harbor-specific labels. Recorded honestly: interactive loop is source-grounded only.
