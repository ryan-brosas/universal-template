<!-- capsule-v2 -->
# OpenCode scope ladder — how does a per-call scope parameter map to read filters vs write identity without a stateful "switch project" command?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when an agent memory tool must let the model choose read/write width per call (this repo / this run / all projects), what are the exact filter and identity shapes per scope, and how does a persisted default coexist with explicit arguments?

## scope.ts — twin ladders with a deliberate global read/write asymmetry
**Path/Symbol:** `integrations/mem0-plugin/.opencode-plugin/scope.ts` — `scopeSearchFilters` (17–32), `scopeWriteParams` (35–50), `asScope` (53–55), `resolveDefaultScope` (63–67), `SCOPE_GUIDANCE` (70–71); consumer precedence in `opencode-mem0.ts` `readScopeFilters` (368–375).
**Signature:** `scopeSearchFilters(scope: Scope, userId, appId, runId): Record<string,string>`; `scopeWriteParams(scope, userId, appId, runId): {user_id; app_id?; run_id?}`; `asScope(value: unknown): Scope`; `resolveDefaultScope(settings: Record<string,unknown>|null|undefined): Scope`.
**Data Shape:** `Scope = "project" | "session" | "global"`. Search: project `{user_id, app_id}`; session `{user_id, app_id, run_id}`; global `{user_id, app_id:"*"}`. Write: project `{user_id, app_id}`; session `{user_id, app_id, run_id}`; **global `{user_id}` only — app_id is dropped**, so the memory lands on the user-wide entity, not a wildcard-filtered project.

### Decisive source
```ts
export function scopeWriteParams(scope: Scope, userId: string, appId: string, runId: string):
  { user_id: string; app_id?: string; run_id?: string } {
  switch (scope) {
    case "session":
      return { user_id: userId, app_id: appId, run_id: runId };
    case "global":
      return { user_id: userId };   // global writes drop app_id so the memory is user-wide, not project-bound
    case "project":
    default:
      return { user_id: userId, app_id: appId };
  }
}
export function asScope(value: unknown): Scope {
  return value === "session" || value === "global" ? value : "project";
}
```
Consumer precedence (`readScopeFilters`): explicit `args.scope` wins → explicit `filters`/`agent_id` take the legacy `resolveFilters` path (which honors the `global_search` setting) → otherwise the persisted default from `~/.mem0/settings.json` `default_scope`, read FRESH per operation so `/mem0-scope` applies without restart; a `"project"` default preserves legacy behavior exactly.

**Flow:** tool call arrives → `asScope` normalizes (only the two literal strings survive; anything else, including numbers and undefined, becomes "project") → search tools build the filter dict, write tools build the identity params → add_memory additionally stamps metadata defaults (confidence 0.7, source "opencode", type task_learning, session_id, files ["*"], branch) and forces `infer=false` when `confidence >= 1.0` and infer was left undefined.
**Invariant:** the global read/write asymmetry must survive any port: searching globally keeps `app_id:"*"` as a FILTER, writing globally OMITS app_id as an IDENTITY key — porting both sides to the same shape either leaks project-bound memories into "global" writes or makes global reads miss them. Normalization is fail-toward-narrowest ("project"), never fail-toward-global; `delete_all_memories` requires an EXPLICIT `scope="global"` to delete user-wide (the injected guidance says so verbatim).
**Probe:** `.opencode-plugin/scope.test.ts` (7 tests, bun green) — pins all three scopes × both ladders, the global-write-drops-app_id line, `resolveDefaultScope(null|undefined|{}) === "project"`, settings-driven defaults, and invalid-value normalization (`42`, `"nonsense"` → "project").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "scopeSearchFilters", limit: 10, fields: ["signature", "name", "file"] });
```
(MCP not connected this session — direct whole-file read of scope.ts + scope.test.ts executed instead; record in verification.md pass 10.)

## Verdict
Adopt the per-call-scope-as-parameter idiom (no stateful switch command), the two-ladder split (filters vs identity), the fail-toward-narrowest normalizer, and the fresh-read persisted default. Adapt the wildcard spelling to your backend's dialect (mem0 core uses `{"OR":[{"user_id":"*"}]}` for global search — see plugin-search-filter-shape.md; this TS surface uses flat `app_id:"*"`). Omit the SCOPE_GUIDANCE copy but keep its semantic: global is opt-in-per-call, never a silent default. Distinct from dsh-per-call-scoping-casing-split.md (that seam is snake/camel casing of the same identity keys; this seam is which keys exist at all). Coverage: fully indexed plane, whole 71L file + 62L test read.
