<!-- capsule-v2 -->
# Total approval config over discovered tools — how do you make a policy config total over a tool surface you don't control (MCP discovery)?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** when an MCP server hands you an arbitrary tool set, how does every uncovered tool get forced through a fallback decision instead of silently running unapproved?

## wrapMcpTools — fill-the-gaps approval wrapper
**Path/Symbol:** `packages/policy-opa/src/wrap-mcp-tools.ts:51` (`export function wrapMcpTools<...>`); no-opinion classifier `isNotApplicable` :115–123; result type `WrappedMcpTools` :9–17.

**Signature:**
```ts
function wrapMcpTools<TOOLS extends Record<string, Tool>, RUNTIME_CONTEXT>(
  tools: TOOLS,
  approval: ToolApprovalConfiguration<TOOLS, RUNTIME_CONTEXT>,
  opts?: { default?: 'approved' | 'denied' | 'user-approval' },
): { tools: TOOLS; toolApproval: ToolApprovalConfiguration<TOOLS, RUNTIME_CONTEXT> };
```

**Data Shape:** returns the SAME `tools` object reference plus a completed `toolApproval`. Default fallback is `'user-approval'` (human in the loop for anything you didn't think about); hard-allowlist mode passes `{default: 'denied'}`.

### Decisive source
```ts
const fallback: ApprovalLiteralStatus = opts?.default ?? 'user-approval';
// function form: shim no-opinion results through the fallback
const wrapped = async args => {
  const status = await approval(args);
  return isNotApplicable(status) ? fallback : status;
};
// map form: total over Object.keys(tools), NOT over the approval keys
const filled = Object.create(null) as Record<keyof TOOLS, unknown>;
for (const name of Object.keys(tools) as Array<keyof TOOLS>) {
  const configured = Object.prototype.hasOwnProperty.call(approval, name)
    ? approval[name] : undefined;
  if (configured == null) filled[name] = fallback;
  else if (typeof configured === 'function') {
    filled[name] = async (...args) => {
      const status = await configured(...args);
      return isNotApplicable(status) ? fallback : status;  // per-tool fns shimmed too
    };
  } else filled[name] = configured;
}
```

**Flow:** discovered tool set + partial approval → generic-function arm gets a `not-applicable`→fallback shim; per-tool-map arm iterates `Object.keys(tools)` (so the result is total over the discovered surface, not the configured one) → unlisted tools get the fallback literal, per-tool FUNCTIONS get wrapped so a no-opinion result also falls back, explicit static entries pass through → `{tools, toolApproval}` returned for direct `generateText` wiring.

**Invariant:** three defenses make "no opinion" impossible to bypass: (1) `isNotApplicable` treats `undefined`, the string `'not-applicable'`, AND `{type:'not-applicable'}` as fallback-eligible — a tool would otherwise resolve to `not-applicable` and run unapproved, defeating the wrapper; (2) the filled map is `Object.create(null)` and reads the supplied approval with an own-property check, so tool names matching inherited object properties (`constructor`, `toString`, `valueOf`) are treated as unconfigured and receive the fallback; (3) the tools object is returned by reference (never cloned), so tool implementations and metadata are untouched.

**Probe:** `packages/policy-opa/src/wrap-mcp-tools.test.ts` (16 cases): function-form not-applicable/string/undefined all fall back (:56–88); same tools reference (:90–92); map-form fills missing tools (:117–130); `default:'denied'` hard-allowlist mode (:144–157); literal `constructor`/`toString`/`valueOf` tools get the fallback (:160–211); per-tool function returning `not-applicable` forced through fallback (:218–236); input/options forwarded to wrapped functions (:284–305).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "wrapMcpTools WrappedMcpTools fallback user-approval", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: wrap-mcp-tools.ts `wrapMcpTools` :51, then its test describe :45.

## Verdict
Adopt the totality-over-discovered-surface pattern for any dynamically discovered capability set (MCP, plugins, extensions); adapt the fallback default to your risk posture (`user-approval` for interactive hosts, `denied` for allowlist-only); omit the SDK approval typing if your host gates tools differently. Coverage caveat: none — fully test-pinned (16 cases).
