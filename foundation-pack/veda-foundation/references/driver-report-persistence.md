<!-- capsule-v2 -->
# Driver-facing report persistence — top-level YAML fields so `yq '.status'` branches directly

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How should a parsed worker report be persisted so downstream automation (or a human) can branch on it without re-parsing?

## report.yaml at session-dir top level + lossless raw_block trace
**Path/Symbol:** `src/util/response-save.ts:saveWorkerReport` (:88–138); sibling `saveResponseYaml` (:32–70); session dir from `src/util/paths:getSessionDir`.
**Signature:** `async function saveWorkerReport(opts: { session; model?; usage?; report: WorkerReport; block?: string }): Promise<string | undefined>`.
**Data Shape:** Writes `<session>/report.yaml` with metadata header (timestamp, persona:'worker', sessionId, model?, usage?) then REPORT FIELDS AT TOP LEVEL: status, salientSummary, whatWasImplemented/LeftUndone, verification, tests?, discoveredIssues?, needs?, raw_block?. Optional fields omitted when empty (`discoveredIssues` only when length > 0).

### Decisive source
```ts
const doc: Record<string, unknown> = {
  timestamp: new Date().toISOString(),
  persona: 'worker',
  sessionId: opts.session,
};
// Worker report fields at the top level (Driver branches on .status/.needs).
doc.status = opts.report.status;
doc.salientSummary = opts.report.salientSummary;
...
if (opts.block) doc['raw_block'] = opts.block;

await Bun.write(filePath, yamlStringify(doc, {
  lineWidth: 120, defaultKeyType: 'PLAIN', blockQuote: 'literal',
}));
return filePath;   // undefined on failure after a console warning — save failure never crashes the run
```

**Flow:** resolve session dir (project `.veda/sessions/<id>` inside a git repo, else `~/.config/veda/sessions/<id>`) → mkdir recursive → build doc with top-level status/needs for direct `yq '.status' report.yaml` consumption → append raw extracted block as lossless trace → write; any error logs a warning and returns undefined.
**Invariant:** The raw `<worker_report>` block rides along as `raw_block` — parser upgrades can re-derive without the original response, and the trace can't disagree with the parsed view. Save failure is degraded to a warning: telemetry must never take down the pipeline. Both savers share the exact yaml options (`lineWidth: 120 / PLAIN keys / literal blocks`) so diffs stay stable.
**Probe:** `tests/util/response-save.test.ts` (:12–90) — pins path layout, full metadata round-trip into YAML, optional-field absence, and overwrite-on-same-session semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "saveWorkerReport response.yaml sessionDir raw_block", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt top-level-field persistence + raw-trace attachment + warn-don't-fail saves for machine-consumed artifacts. Adapt file format/location to your host's session conventions. Omit the usage block if your backends don't meter.
