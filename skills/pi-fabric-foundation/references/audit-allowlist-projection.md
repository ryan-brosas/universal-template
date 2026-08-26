<!-- capsule-v2 -->
# Audit allowlist projection — how do you keep invocation args/results in a durable trace without a secret-shaped string slipping through?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the primary confidentiality boundary for what a durable audit retains?

## Exact-ref allowlist + typed field copiers
**Path/Symbol:** `src/audit/projection.ts:projectFabricAuditArgs` (:164-270), `projectFabricAuditResult` (:276-303); copiers `copyString/copyNumber/copyIdentifier/copyPath` (:63-113), path guard `localPath` (:35-61).
**Signature:** `projectFabricAuditArgs(ref: string, args: Record<string, unknown>): { value: {}; droppedValues: number }`; same shape for results, plus `undefined` = "omit entirely".
**Data Shape:** per-ref switch; unknown/extension/MCP/schema/state/compact/generic calls → `emptyProjection(args)` (empty object, droppedValues = top-level key count). The 24 `agents.*` actions keep ONLY `id`; `pi.bash` keeps only `command`; file tools keep only bounded `path` (+offsets/limits); mesh tools keep topic/to/key/prefix.

### Decisive source
```ts
/**
 * Projects invocation arguments by exact built-in reference. Unknown,
 * extension, MCP, schema, state, compact, and generic provider calls retain no
 * arguments. This allowlist, rather than secret-looking string matching, is
 * the durable trace's primary confidentiality boundary.
 */
export const projectFabricAuditArgs = (ref, args) => {
  switch (ref) {
    case "fabric.discovery.providers":
    case "fabric.discovery.models":
    case "fabric.workflow.progress":
      return emptyProjection(args);
    ...
    default:
      if (idOnlyAgentActions.has(ref)) return projected(args, (o) => copyString(o, args, "id"));
      return emptyProjection(args);
  }
};
```
```ts
// localPath(): never retain URL userinfo or query credentials as a "path"
const absolute = new URL(value);
if (absolute.protocol) return undefined;
...
const based = new URL(value, "https://fabric.invalid/");
if (based.hostname !== "fabric.invalid") return undefined;   // protocol-relative guard
```

**Flow:** build() copies only allowlisted fields via type-checked copiers (`copyIdentifier` accepts `[A-Za-z0-9]` plus `-./:_` after position 0 — no free text) → ANY throw inside build falls back to `emptyProjection` (projection failure degrades to omission, never raw retention) → results are omitted for everything except `pi.write`'s boolean creation outcome (`created:true` at top level OR under `details`) and `fabric.approval.auto`'s identifier fields.
**Invariant:** default-deny by exact ref — a NEW built-in is invisible to the trace until someone adds it to the allowlist (safe-by-default drift); secret-looking-string matching is explicitly NOT the mechanism; paths are stripped of query/fragment and rejected if they parse as URLs with a scheme or cross-origin base resolution.
**Probe:** `tests/audit-trace.test.ts:799` ("retains bash commands while omitting arbitrary argument and result content"), `:921` ("retains identifiers for every actor-targeting management action"), `:136` ("records all discovery paths in issue order without queries or results").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "projectFabricAuditArgs projectFabricAuditResult idOnlyAgentActions copyIdentifier localPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-ref default-deny projection with typed copiers and the URL-vs-path discrimination; adapt the ref table and per-field choices to your tool registry; omit nothing structural — the fallback-to-empty-on-throw wrapper IS the safety property. Direct tests cited; graph coverage clean.
