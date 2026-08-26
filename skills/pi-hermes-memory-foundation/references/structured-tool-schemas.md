<!-- capsule-v2 -->
# Structured-field tool schemas — action-split tools and structured list fields that render Markdown so the model never hand-writes formatting

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you design LLM-facing write tools so small models cannot produce malformed arguments — by splitting one do-everything tool into per-action schemas, accepting typed arrays instead of Markdown lists, and validating with a strict required-field ladder?

## registerSkillTool + registerActionTool
**Path/Symbol:** `src/tools/skill-tool.ts:registerSkillTool` (:92–333), `buildStructuredSkillBody` (:31–50), patch section resolution (:228–263); `src/tools/memory-tool.ts:registerActionTool` (:351–373).
**Signature:** `skill_manage {action: create|view|patch|update|edit|delete, name?, skill_id?, description?, scope?, section?, content?, when_to_use?, procedure_steps?: string[], pitfalls?: string[], verification_steps?: string[]}` — `additionalProperties: false`.
**Data Shape:** structured fields render deterministically: procedure/verification → `"1. …\n2. …"` ordered lists; pitfalls → `- …` bullets (empty ⇒ "No notable pitfalls recorded yet."); body skeleton = `## When to Use / ## Procedure / ## Pitfalls / ## Verification`.

### Decisive source
```ts
// MEMORY TOOLS: one schema per action — the target's required params are
// enforced by the SCHEMA, not by runtime branching:
registerActionTool("add",    "memory_add",    …, Type.Object({ target, content, category?, failure_reason? }));
registerActionTool("replace","memory_replace",…, Type.Object({ target, old_text, content }));
registerActionTool("remove", "memory_remove", …, Type.Object({ target, old_text }));

// SKILL PATCH: prefer the structured field matching the section…
const sectionKey = section.replace(/^#+\s*/, "").trim().toLowerCase();
if (sectionKey === "procedure" && procedureSteps.length > 0) patchContent = formatOrderedList(procedureSteps);
else if (sectionKey === "pitfalls" && pitfallItems.length > 0) patchContent = formatBulletList(pitfallItems, …);
// …then accept a SINGLE unambiguous structured field for non-standard sections:
} else if (!patchContent && hasStructuredBody) {
  if (procedureSteps.length > 0 && pitfallItems.length === 0
      && verificationSteps.length === 0 && !whenToUse) { patchContent = formatOrderedList(procedureSteps); }
  else if (/* exactly-one-field variants */) { … }
  else {
    return { error: "For patch, provide content or exactly one structured field matching the target "
                   + "section … Use update for multi-section rewrites." };
  }
}

// CREATE ladder: content OR structured fields; if structured, ALL THREE of
// when_to_use, procedure_steps, verification_steps are required:
if (!whenToUse) return { error: "when_to_use is required when content is omitted." };
if (procedureSteps.length === 0) return { error: "procedure_steps is required when content is omitted." };
if (verificationSteps.length === 0) return { error: "verification_steps is required when content is omitted." };
```

**Flow:** (1) the schema itself rejects wrong-shaped calls before execute runs (`additionalProperties: false`, StringEnum actions/scopes/categories); (2) create/update build bodies from structured fields or accept raw `content`; (3) patch maps a section header to its structured field and renders lists; ambiguity (multiple structured fields, no section match) is an explicit ERROR naming the remedy (`update`), never a guess; (4) results return as JSON in `content` plus a typed `details` object that drives the TUI summary.
**Invariant:** every error message names the NEXT VALID MOVE (which field, which action) — errors are prompts, not failures; free-form `content` remains a universal escape hatch but is documented as inferior to structured fields ("Prefer structured fields over free-form content"); the legacy alias `edit` survives inside the enum rather than as a separate tool.
**Probe:** `tests/tools/skill-tool.test.ts` (478 L: create validation order, patch single-field inference, edit aliasing, delete); `tests/tools/memory-tool.test.ts`. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "registerSkillTool buildStructuredSkillBody registerActionTool", limit: 5 })`

## Verdict
Adopt for any LLM-facing mutation API: action-split schemas, typed array fields rendered to canonical text server-side, ambiguity → instructive error. Adapt section names and field sets. Pair with `tool-result-summary-views.md` for the response side of the same philosophy.
