<!-- capsule-v2 -->
# Mode persona routing — how does one agent serve multiple personas whose tool surfaces differ per model?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter adds switchable personas — who picks the persona, and how is the visible tool set computed without per-message allocation?

## Model-driven selection advertised in the prompt; tools filtered through alias-aware group math
**Path/Symbol:** `src/core/prompts/sections/modes.ts:8-35` (`getModesSection`); `src/core/prompts/tools/filter-tools-for-mode.ts:14-46` (precomputed alias maps), `:63-86` (RENAMED_TOOL_CACHE), `:152-210` (`applyModelToolCustomization`), `:225-330` (`filterNativeToolsForMode`); mode data in `src/shared/modes.ts`.
**Signature:** ModeConfig = `{slug, name, roleDefinition, whenToUse?, groups: (ToolGroup | [ToolGroup, ...opts])[]}`; `filterNativeToolsForMode(nativeTools, mode, customModes, experiments, codeIndexManager?, settings?, mcpHub?)`.
**Data Shape:** Three module-load maps: alias→canonical, canonical→aliases, any-name→frozen alias GROUP (O(1)). Model customization = `modelInfo.excludedTools` removes; `modelInfo.includedTools` adds ONLY if the tool's group is allowed by the current mode, tracking alias renames.

### Decisive source
```ts
if (mode.whenToUse && mode.whenToUse.trim() !== "") {
	description = mode.whenToUse.replace(/\n/g, "\n    ");
} else {
	description = mode.roleDefinition.split(".")[0];   // first-sentence fallback
}
return `  * "${mode.name}" mode (${mode.slug}) - ${description}`;
```
And the corruption fallback (:241-243): a missing/deleted custom mode config falls back to `defaultModeSlug` so the agent always has functional tools.

**Flow:** system prompt renders every mode as `"Name" mode (slug) - description` → THE MODEL switches personas by calling `new_task` with a slug (no hard-coded router) → tool surface = groups ∩ permission checks ± model customization − conditional exclusions (codebase_search unconfigured, todo list disabled, experiments off, settings.disabledTools with ALIAS NORMALIZATION so disabling a legacy alias kills the canonical tool too) → renamed definitions served from RENAMED_TOOL_CACHE keyed `canonical:alias` to avoid per-message object churn.
**Invariant:** Persona switching is data + prompt advertisement, never code; tool filtering must be idempotent under aliasing — an operation naming ANY member of an alias group must affect the whole group.
**Probe:** `src/core/prompts/tools/__tests__/filter-tools-for-mode.spec.ts` (:77 "disables canonical tool when disabledTools contains alias name"); section rendering pinned by `src/core/prompts/__tests__/system-prompt.spec.ts` (:58 mocks `../sections/modes`, :439 asserts mode roleDefinition ordering before "TOOL USE" — no dedicated sections.spec.ts exists at this pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "filterNativeToolsForMode applyModelToolCustomization getModesSection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenToUse-advertised personas + group-based filtering with alias normalization. Adapt group vocabulary to your tool set. Omit the rename cache if you don't alias tools. Coverage caveat: none.
