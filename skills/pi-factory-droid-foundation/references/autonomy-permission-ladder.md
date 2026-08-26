<!-- capsule-v2 -->
# Autonomy permission ladder — how do autonomy levels map to confirmation outcomes without nagging per step?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** The remote agent has its own autonomy level deciding WHEN to ask for confirmation; when it does ask, how do I honor the configured level instead of prompting the human on every action?

## autoLevel → ProceedAutoRun outcome short-circuit with env escape hatch
**Path/Symbol:** `src/providers.ts:createPermissionHandler` (807-826), `isPromptAlwaysEnabled` (828-831), `promptViaUi` (833-849), `autonomyFromAutoLevel` (866-870), `handleAskUser` (851-864).
**Signature:** `createPermissionHandler(cfg: ResolvedConfig, runtime?: InstanceRuntime): (params: RequestPermissionRequestParams) => Promise<ToolConfirmationOutcome>`
**Data Shape:** `cfg.autoLevel: "low" | "medium" | "high" | <default/prompt>`; handler receives tool-use descriptors (`toolUses[].{toolUse, details}` where details may carry `fullCommand` or `filePath`); returns a confirmation-outcome enum.

### Decisive source
```ts
if (!isPromptAlwaysEnabled()) {
  switch (cfg.autoLevel) {
    case "high":   return ToolConfirmationOutcome.ProceedAutoRunHigh;
    case "medium": return ToolConfirmationOutcome.ProceedAutoRunMedium;
    case "low":    return ToolConfirmationOutcome.ProceedAutoRunLow;
    default:
      // fall through to UI prompt below
      break;
  }
}
return promptViaUi(params, runtime);
```

Escape hatch and no-UI boundary:
```ts
function isPromptAlwaysEnabled(env = process.env): boolean {
  const raw = env.PI_DROID_PROMPT_ALWAYS?.trim().toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes" || raw === "on";
}
...
const ui = runtime?.ui ?? null;
if (!ui) return ToolConfirmationOutcome.Cancel;
// summary = tool name + fullCommand|filePath, joined, sliced to 2000 chars
const approved = await ui.confirm("Droid requests permission", summary || "Allow this operation?");
return approved ? ToolConfirmationOutcome.ProceedOnce : ToolConfirmationOutcome.Cancel;
```

The level ALSO gates when Droid asks at all — set at session creation:
```ts
function autonomyFromAutoLevel(level: ResolvedConfig["autoLevel"]): AutonomyLevel {
  if (level === "high") return AutonomyLevel.High;
  if (level === "medium") return AutonomyLevel.Medium;
  return AutonomyLevel.Low;
}
```

**Flow:** session created with BOTH the mapped `autonomyLevel` and this handler → remote decides which calls warrant confirmation → when asked, the handler short-circuits to the matching auto-run outcome unless PI_DROID_PROMPT_ALWAYS forces the UI path → UI path degrades to Cancel when no UI is bound. `handleAskUser` follows the same no-UI-cancel pattern and cancels the WHOLE batch if any question is dismissed.
**Invariant:** `autoLevel: "high"` must mean "no prompts", never "prompt every step"; an audit-minded user can force prompting via env without code changes; absence of UI must deny, not approve.
**Probe:** `test/permissions.test.ts:27-43` (high/medium/low each return their ProceedAutoRun* without consulting UI); `:45-57` (PI_DROID_PROMPT_ALWAYS=1 + no UI ⇒ Cancel, env restored in finally); `:59-67` (isPromptAlwaysEnabled accepts 1/true/yes/on case-insensitively, rejects 0/false/empty/absent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "createPermissionHandler isPromptAlwaysEnabled promptViaUi autonomyFromAutoLevel", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the two-sided contract: map the host's autonomy level onto the remote's own gating AND onto the confirmation outcomes returned when asked; keep the always-prompt env override and deny-by-default without UI. Adapt enum names and env var to your stack. Omit Pi's ui.confirm/ui.select plumbing specifics.
