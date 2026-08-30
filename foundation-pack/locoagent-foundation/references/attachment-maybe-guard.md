<!-- capsule-v2 -->
# Collector error isolation — how do 30 independent context probes fail without failing each other?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the uniform guard that turns any collector crash into an empty contribution plus telemetry.

## maybe
**Path/Symbol:** `src/utils/attachments.ts:maybe` (:1005-1042).
**Signature:** `async function maybe<A>(label: string, f: () => Promise<A[]>): Promise<A[]>` — label is a stable collector name ('changed_files', 'plan_mode', …).
**Data Shape:** takes a thunk returning attachment arrays; ALWAYS resolves to an array — [] on error.

### Decisive source
```ts
try {
  const result = await f()
  const duration = Date.now() - startTime
  // Log only 5% of events to reduce volume
  if (Math.random() < 0.05) {
    logEvent('tengu_attachment_compute_duration', { label, duration_ms: duration,
      attachment_size_bytes, attachment_count: result.length })
  }
  return result
} catch (e) {
  if (Math.random() < 0.05) logEvent('...duration', { label, duration_ms, error: true })
  logError(e)
  logAntError(`Attachment error in ${label}`, e)
  return []
}
```

**Flow:** wrap → run → sample 5% success/error telemetry with byte-size accounting (note the `jsonStringify(undefined)` guard comment justifying the pre-filter) → on ANY rejection log and resolve []. The label makes failures attributable per-collector in dashboards. The orchestrator additionally filters null/undefined AFTER flattening, so even a misbehaving thunk returning `[undefined]` cannot crash rendering.
**Invariant:** no collector may reject through this layer; a new collector that can throw synchronously must still be handed to `maybe` as a thunk returning a promise (wrap sync fns in `Promise.resolve`). Telemetry volume control (sampling) is part of the contract — un-sampled per-turn logging from ~30 collectors floods the pipeline.
**Probe:** deterministic grep probe: every entry in the `allThreadAttachments` / `mainThreadAttachmentArrays` literals is wrapped — `grep -A1 "maybe('" src/utils/attachments.ts | wc -l`. No upstream test (coverage caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "maybe attachment compute duration logError", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt labeled-thunk isolation with sampled duration+error telemetry; adapt event names; omit Ant-only error mirroring. Porting trap: catching inside each collector instead of one wrapper loses uniform latency/error attribution; not wrapping at all means one denied-stat kills every other attachment kind that turn.
