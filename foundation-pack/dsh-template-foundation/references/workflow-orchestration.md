<!-- capsule-v2 -->
# Workflow orchestration — the DSH `workflow` tool shape and parallel fan-out

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does DSH's `workflow` tool orchestrate a JavaScript script that fans work out across many subagents with phases and structured results, and what is the disciplined parallel fan-out pattern?

## DSH workflow orchestration
**Path/Symbol:** `.dsh/workflows/README.md` (whole file) — the `workflow` tool shape (`meta`/`script`/`args`), the parallel fan-out pattern, and the discipline section.
**Signature:** the `workflow` tool takes `meta` (required identity: `name`, `description`, optional progress annotations), `script` (plain JS orchestration body — no `export const meta`), and `args` (optional JSON object exposed as the `args` global). Completion returns canonical `{ runId, agentsStarted, result }`.
**Data Shape:** the script body is plain JavaScript (no `export const meta`); `args` is exposed as a global; wrap a bare list in a field so the wire schema stays honest. The fan-out API forks subagents that each return a `result`.

### Decisive source
```js
// Parallel fan-out: delegate independent units, then reconcile.
const [analysis, research] = await Promise.all([
  forkAnalysis(args),
  forkResearch(args),
]);
return { analysis: analysis.result, research: research.result };
```

**Flow:** (1) only use the `workflow` tool on an explicit user ask for a workflow / large multi-agent orchestration (for one or two delegations, prefer plain subagent calls); (2) author the script body with `meta`/`script`/`args`; (3) fan independent units out in parallel via `Promise.all`; (4) reconcile delegated results against durable state (`fabric_mesh`) before relying on them; (5) the parent turn blocks until the whole workflow settles.

**Invariant:** the workflow tool is reserved for explicit large-orchestration requests; each delegated unit is self-contained with a defined result contract; delegated results are reconciled against durable state before use; a bare list in `args` is wrapped in a field to keep the wire schema honest.

**Probe:** no direct test file exists. Verified by direct source read (`.dsh/workflows/README.md`; the `workflows/` dir presence is checked by `check.mjs`). The `meta`/`script`/`args` shape and `Promise.all` fan-out are the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "workflow meta script args fan-out subagent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `workflow` tool `meta`/`script`/`args` shape, the `Promise.all` parallel fan-out, and the reconcile-against-durable-state discipline. Adapt the fork functions and result contracts to the host. Omit for one-or-two delegations (prefer plain subagent calls).
