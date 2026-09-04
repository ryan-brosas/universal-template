<!-- capsule-v2 -->
# Run protocol exit contract — how should a single-run CLI handler keep stdout machine-parseable while persona post-processing changes what "success" means?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A CLI that wraps an LLM call must serve two consumers at once — humans reading stderr, and driver programs piping stdout — while persona-specific protocols (design blocks, worker reports) add their own failure modes. How are exit codes and output channels structured so a driver never misparses?

## Protocol health controls the exit code, not the task outcome
**Path/Symbol:** `src/commands/run.ts:handleRun` (whole, 346L): resolution (:19-27), context assembly (:55-90), worker §7 ladder (:225-268), stdout discipline (:271-301), exit-code contract (:307-309); direct test `tests/commands/worker-run.test.ts` (178L whole).
**Signature:** `handleRun(prompt: string, options: CliOptions) → Promise<void>` (exits via `process.exit`).
**Data Shape:** `workerResult` is a discriminated union: `{ ok: true; block: string; report: WorkerReport; path?: string; warnings: string[] }` | `{ ok: false; reason: 'no-block' | 'malformed'; detail?: string; tail: string }` | `undefined` (non-worker personas).

### Decisive source
```ts
  } else if (workerResult) {
    // In text mode the <worker_report> block is the only thing on stdout — a
    // Driver can pipe stdout straight into a parser while the trace runs to
    // stderr. On protocol failure nothing is echoed; the error is on stderr.
    if (workerResult.ok) {
      console.log(workerResult.block);
    }
  }
  // Protocol health controls the exit code, not the task outcome: a
  // well-formed report that truthfully says failed/blocked exits 0; a missing
  // or malformed block is a failure of the run itself.
  if (isWorker && workerResult && !workerResult.ok) {
    process.exit(1);
  }
```
The §7 parse-failure ladder (worker branch):
```ts
    const parsed = parseWorkerReport(response.text);
    if (parsed.ok) {
      const reportPath = await saveWorkerReport({ ... });
      // well-formed → persist + echo block, exit 0 (even if status is
      // failed/blocked — a truthful verdict is a successful delegation)
    } else {
      // missing required field → persist what parsed, warn, exit 0
      // no block / malformed → protocol error with the tail, exit non-zero
    }
```
**Flow:** resolve backend/model (loud exit 1 if backend unavailable) → assemble context (selection store + ad-hoc files + design.json auto-attach for reviewer/worker) → `runLlm` → save response.yaml BEFORE echoing the body (so the path is visible even when stdout truncates) → persona-conditional post-processing: `navigator-plan` gets design parse/validate/write with exit 1 on validation failure or missing block; `worker` gets the §7 ladder → stdout: worker text mode echoes ONLY the `<worker_report>` block; JSON mode emits one structured document including `worker: {ok, status, path, warnings}` or `worker: {ok: false, reason, detail}` → exit 1 only on protocol failure (no-block/malformed), never on a truthful `failed`/`blocked` status.
**Invariant:** stdout carries exactly one thing per mode (the block, the JSON document, or the plain response); all diagnostics (header, tool events, report path, warnings, protocol errors) go to stderr. A well-formed report that truthfully says the task failed is a SUCCESSFUL delegation (exit 0) — the driver branches on `report.yaml`'s `.status`, not on the exit code.
**Probe:** `tests/commands/worker-run.test.ts` (executed live at pin: 6 pass / 0 fail) pins stdout-is-block-only, report.yaml persistence with Factory field names, blocked-status exit 0, no-block exit 1 with nothing on stdout, malformed exit 1, and trailing-prose-after-block exit 1.
**Coverage caveat:** the navigator-plan design branch of handleRun has no direct integration test (design-parse/validate/write capsules carry their own suites); its exit-code behavior is source-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "handleRun worker_report protocol exit code stdout stderr parseWorkerReport saveWorkerReport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-channel output discipline (stdout = parseable payload, stderr = everything else) and the protocol-health exit contract (truthful failure verdicts exit 0; malformed protocol exits 1). Adapt the persona set and the report vocabulary to your host. Omit the design auto-attach if your host has no design-contract plane.
