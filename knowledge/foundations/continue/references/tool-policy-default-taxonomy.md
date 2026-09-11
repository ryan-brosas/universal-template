<!-- capsule-v2 -->
# Tool-policy default taxonomy — how should a tool registry split its permission defaults so reads stay fluid but dangerous surfaces still gate?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter assign per-tool default permissions across a built-in registry such that "readonly" alone does not decide safety, and what resolves when user, definition, and dynamic evaluation disagree?

## Four (readonly, defaultToolPolicy) families over 20 definitions + a three-level resolution ladder with monotone clamping

**Path/Symbol:** census over `core/tools/definitions/*.ts` (exactly 20 files; grep census `defaultToolPolicy|readonly:` = 39 matches, decisive reads readSkill.ts whole 34L, requestRule.test.ts whole 239L); resolution in `gui/src/redux/thunks/evaluateToolPolicies.ts` whole (121L); global default `gui/src/redux/slices/uiSlice.ts:34`.
**Signature:** `evaluateToolPolicy(ideMessenger, activeTools, toolCallState, toolPolicies): Promise<EvaluatedPolicy>`; `DEFAULT_TOOL_SETTING: ToolPolicy = "allowedWithPermission"`.
**Data Shape:** ToolPolicy ∈ `"allowedWithoutPermission" | "allowedWithPermission" | "disabled"`; per-tool fields `readonly: boolean`, optional `defaultToolPolicy?: ToolPolicy`.

### Census result (this pass, source lines verified)
```
free reads        readonly:true  + allowedWithoutPermission ×7:
                  readFile :13/:36, readFileRange :16/:53, ls :14/:36,
                  viewDiff :11/:25, grepSearch :10/:29, globSearch :10/:28,
                  searchWeb :11/:28
gated writes      readonly:false + allowedWithPermission    ×5:
                  createNewFile :14/:36, editFile :23/:44,
                  singleFindAndReplace :22/:75, multiEdit :26/:112,
                  runTerminalCommand :41/:63
GATED READS       readonly:true  BUT allowedWithPermission   ×5:
                  readCurrentlyOpenFile :10/:22, fetchUrlContent :10/:28,
                  codebaseTool :10/:29, viewRepoMap :11/:25,
                  viewSubdirectory :13/:35
disabled meta     readonly:false + disabled                  ×2:
                  requestRule :47/:66, createRuleBlock :24/:62
no default        readSkill (async GetTool embedding live skill names
                  into its description) ⇒ falls through to DEFAULT_TOOL_SETTING
```

### Decisive source (resolution + clamp)
```ts
if (isEditTool(toolCallState.toolCall.function.name)) {
  return { policy: "allowedWithoutPermission", toolCallState };   // edit family bypasses ALL of it
}
const basePolicy = toolPolicies[name]                              // 1. user setting
  ?? activeTools.find(...)?.defaultToolPolicy                      // 2. definition default
  ?? DEFAULT_TOOL_SETTING;                                         // 3. global default
if (result.status === "error") return { policy: "disabled", ... };// protocol error ⇒ fail-closed
if (basePolicy === "disabled") return disabled;                    // sticky floor
if (basePolicy === "allowedWithPermission" && dynamicPolicy === "allowedWithoutPermission")
  return allowedWithPermission;                                    // cannot relax
```

**Flow:** the GUI evaluates every generated tool call through this thunk, sending `tools/evaluatePolicy` to core for arg-dependent refinement (file-access ladder / terminal veto capsules own that half); disabled results dispatch `errorToolCall` plus a "Security Policy Violation" context item carrying the server-provided displayValue (:97–118). The gated-reads family is the taxonomy's key lesson: touching IDE-open files, external URLs, indexed code, or the repo map is readonly in the mutation sense but NOT in the exfiltration/latency sense, so they default behind permission despite `readonly: true`. The two `disabled` meta-tools mutate configuration itself (requestRule/createRuleBlock), so they ship off until a user enables them.
**Invariant:** resolution is override-laddered (user > definition > global) and refinement is MONOTONE — dynamic evaluation may only escalate toward more restrictive, never relax (`disabled` is sticky, permission cannot become silent). Edit-family tools bypass everything unconditionally by design.
**Probe:** `core/tools/definitions/requestRule.test.ts` (whole 239L, 9 cases) pins the meta-tool's dynamic description surface: only rules with `alwaysApply: false` AND no globs are listed as agent-requestable; missing name/description interpolate literal "undefined"; empty set renders "No rules available." — the description IS the tool's entire UX since it ships disabled. GUI-side ladder has no dedicated suite (recorded caveat); its clamp logic is mirrored and pinned server-side by runTerminalCommand.vitest.ts :740–860.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "tool definition readonly defaultToolPolicy allowedWithoutPermission allowedWithPermission", limit: 10 });
```

## Verdict
Adopt the four-family taxonomy and the three-level ladder with monotone clamping; adapt which surfaces count as "gated reads" to your threat model; omit the edit-family bypass if your editor tools flow through the same prompt loop. Trap: a definition that merely forgets `defaultToolPolicy` silently inherits the permissive-with-prompt global default — treat a missing field as a decision, not an omission (readSkill proves the fallback path is real).
