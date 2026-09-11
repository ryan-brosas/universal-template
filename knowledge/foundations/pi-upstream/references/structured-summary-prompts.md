<!-- capsule-v2 -->
# Structured summary prompts — what contract makes a summary safe to hand back to an LLM as context?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter's summarizer drifts into answering the user or loses earlier facts on re-compaction — how is the prompt shaped?

## Anti-continuation system prompt + exact sections + PRESERVE-and-ADD updates
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:424-459` (`SUMMARIZATION_SYSTEM_PROMPT`, `SUMMARIZATION_PROMPT`), `:461-498` (`UPDATE_SUMMARIZATION_PROMPT`), `:689-702` (`TURN_PREFIX_SUMMARIZATION_PROMPT`); assembly in `generateSummaryWithUsage` at `:529-593`.
**Signature:** prompt assembly: `<conversation>…</conversation>\n\n` [+ `<previous-summary>…</previous-summary>\n\n`] + base prompt [+ `\n\nAdditional focus: <customInstructions>`]; single user message; shared summarization system prompt.
**Data Shape:** Exact section skeleton enforced in BOTH create and update variants: Goal / Constraints & Preferences / Progress (Done · In Progress · Blocked) / Key Decisions / Next Steps / Critical Context.

### Decisive source
```ts
const SUMMARIZATION_SYSTEM_PROMPT = `You are a context summarization assistant. ... Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary.`;
// UPDATE variant rules:
// - PRESERVE all existing information from the previous summary
// - ADD new progress, decisions, and context from the new messages
// - UPDATE the Progress section: move items from "In Progress" to "Done"
// - PRESERVE exact file paths, function names, and error messages
```
Both variants end with: "Keep each section concise. **Preserve exact file paths, function names, and error messages.**"

**Flow:** serialize the summarized range with `serializeConversation` (`[User]:` / `[Assistant thinking]:` / `[Assistant]:` / `[Assistant tool calls]: name(k=v, …)` / `[Tool result]:` truncated at 2000 chars with a "[... N more characters truncated]" tail marker) → wrap in `<conversation>` → choose create vs UPDATE prompt by presence of previousSummary → append file-op ledgers as `<read-files>` / `<modified-files>` tags AFTER generation (`formatFileOperations`) so they are deterministic, not model-recalled.
**Invariant:** The summary must read as a checkpoint document, not a conversational reply; iterative compaction must be monotone (PRESERVE-and-ADD) or earlier facts decay; exact identifiers survive verbatim because the prompt demands it twice.
**Probe:** `packages/agent/test/harness/compaction.test.ts:441/:496/:523` ("serializes conversation with truncated tool results" / "includes previous summaries and custom instructions in generateSummary prompts" / "preserves the string result from generateSummary").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "SUMMARIZATION_PROMPT serializeConversation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt anti-continuation framing, exact-section skeletons, preserve-and-add update semantics, and deterministic file-op tags appended post-generation. Adapt section names to your domain. Omit the turn-prefix prompt if you don't port split turns. Coverage caveat: none.
