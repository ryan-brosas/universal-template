<!-- capsule-v2 -->
# Directive wall vs context injection — two prompt modes where pinned rules ride EVERY session and memories ride on demand

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you restructure agent memory from "inject everything into the system prompt" to "inject only a behavioral policy, keep memories searchable" — while guaranteeing user-pinned rules still reach every session?

## buildPromptContext + resolveMemoryPolicyPrompt
**Path/Symbol:** `src/prompt-context.ts:resolveMemoryPolicyPrompt` (:8–24), `buildPromptContext` (:33–55); composition wiring `src/index.ts:222-230` (`before_agent_start` handler); consumer preview `src/handlers/preview-context.ts:registerPreviewContextCommand` (:25–105).
**Signature:** `buildPromptContext(config, store, projectStore, projectName, standing?) → Promise<string>` (empty string = inject nothing); `resolveMemoryPolicyPrompt({memoryPolicyStyle, memoryPolicyCustomText}) → string`.
**Data Shape:** config axes `memoryMode: "policy-only" | "legacy-inject"` × `memoryPolicyStyle: full | compact | custom | none`; block order in legacy mode: MEMORY → PROJECT → STANDING.

### Decisive source
```ts
/**
 * Standing instructions are appended in *every* mode, including policy-only
 * and policy style "none". That is the whole point of the store: a rule the
 * user pinned must not depend on the model choosing to run memory_search
 * before the action it forbids (#121). They go last so they read as the
 * operative directive rather than as recalled context.
 */
export async function buildPromptContext(config, store, projectStore, projectName, standing = null): Promise<string> {
  const standingBlock = standing?.formatForSystemPrompt() ?? "";
  if (config.memoryMode === "policy-only") {
    return [resolveMemoryPolicyPrompt(config), standingBlock].filter(Boolean).join("\n\n");
  }
  const memoryBlock = store.formatForSystemPrompt();
  const projectBlock = projectStore ? projectStore.formatProjectBlock(projectName) : "";
  const parts: string[] = [];
  if (memoryBlock) parts.push(memoryBlock);
  if (projectBlock) parts.push(projectBlock);
  if (standingBlock) parts.push(standingBlock);
  return parts.join("\n\n");
}
```
Custom-style fallback: empty/whitespace custom text silently becomes the COMPACT policy — a missing override degrades visible, never blank.

## The structural writer wall (/memory-pin)
**Path/Symbol:** `src/handlers/standing-pin.ts:registerStandingPinCommand` (:52–111); header comment (:1–8); composition-root comment `src/index.ts:159-163`.
**Data Shape:** subcommands `list|remove <n>|clear|<text>`; list output renders live budget usage (`N/MAX_ENTRIES entries · used/MAX_CHARS chars`), injected count, over-budget omissions.

### Decisive source
```ts
/**
 * /memory-pin — the only writer of STANDING.md besides the user's own editor.
 *
 * Deliberately not a tool: background review, consolidation and the correction
 * detector must have no path into the always-injected block (#121). Keeping it
 * a slash command makes model-authored standing instructions structurally
 * impossible rather than merely forbidden by prompt.
 */
```

**Flow:** (1) at `before_agent_start` the composed block is APPENDED to the host system prompt (only when non-empty); (2) policy-only mode ships a compact instruction telling the model WHEN to call `memory_search` (memories become retrieval-on-demand via the dual-write mirror); (3) the standing block rides both modes, positioned LAST so it reads as operative directive, not recalled context; (4) `/memory-preview-context` renders the exact injected blocks plus counts so users can audit what the model sees.
**Invariant:** the injection channel split is by TRUST: user-authored rules = unconditional + structurally unwritable by the model (slash command, not tool); model-derived memories = conditional + searchable. Prompt-level prohibitions ("never write standing instructions") are treated as insufficient — provenance enforcement is positional/structural. Empty blocks are omitted entirely (no placeholder noise).
**Probe:** `tests/handlers/prompt-context.test.ts` + `tests/handlers/system-prompt.test.ts` (policy style resolution incl. custom-fallback-to-compact; standing block present in policy-none mode; block ordering); `tests/handlers/preview-context.test.ts` (block counting). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "buildPromptContext resolveMemoryPolicyPrompt registerStandingPinCommand", limit: 5 })`

## Verdict
Adopt the two-channel design for any agent-memory system. Adapt policy texts, mode names, and the fenced-block marker. Extends (does not duplicate) the existing `standing-instructions.md` capsule: that one owns the STORE mechanics; this one owns the INJECTION architecture and the writer wall.
