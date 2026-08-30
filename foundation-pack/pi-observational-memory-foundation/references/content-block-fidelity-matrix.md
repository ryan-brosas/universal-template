<!-- capsule-v2 -->
# Content-block fidelity matrix — which non-text blocks are dropped, shown as evidence, or replaced by a placeholder, per role and dialect

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When session content must cross a text-only boundary — bounded observer input one way, raw recall evidence the other — what happens to each content-block type (text / thinking / redacted thinking / toolCall / garbage), and how do the option flags select per role?

## Path/Symbol
`src/serialize.ts` — `textAndPlaceholders` :27-60, `textOnly` :62-70, call sites in `serializeConversation` :72-96, `renderCustomMessage` :121-139, `renderRecallMessage` :238-257.
**Signature:** `textAndPlaceholders(content: unknown, options?: { omitRedactedThinking?: boolean; includeThinking?: boolean }): string`; `textOnly(content: unknown): string`.
**Data Shape:** content is a string OR an array of loosely-typed blocks (`{ type?, text?, redacted?, thinking?, name?, arguments? }`) — every block field is duck-checked; nothing throws.

### Decisive source
```ts
// serialize.ts:44-52 — thinking triage is the heart of the matrix
if (block.type === "thinking") {
	if (options.omitRedactedThinking && block.redacted === true) continue; // dropped ENTIRELY (no line)
	if (options.includeThinking && typeof block.thinking === "string") {
		parts.push(`[thinking: ${block.thinking}]`);                          // kept as labeled evidence
		continue;
	}
	parts.push("[non-text content omitted]");                                // degrades to placeholder
	continue;
}
```
```ts
// serialize.ts:53-57 + 62-70 — toolCall keeps its identity; textOnly drops silently
if (block.type === "toolCall" && typeof block.name === "string") {
	parts.push(`[${block.name}(${JSON.stringify(block.arguments ?? {})})]`);
}
function textOnly(content: unknown): string {
	...
	.filter((b): b is TextContent => b?.type === "text" && typeof b.text === "string")
```

**Flow (the full call-site matrix):**
| Dialect | Role | Helper + options | Non-text outcome |
|---|---|---|---|
| observer-input (`serializeConversation`) | user, toolResult | `textOnly` | SILENTLY dropped — no placeholder at all |
| observer-input | assistant | `textAndPlaceholders({includeThinking:true, omitRedactedThinking:true})`, blank lines filtered; empty body ⇒ whole message skipped | thinking = `[thinking: …]`; redacted = gone; toolCall = `[name({…})]` |
| recall (`renderRecallMessage`) | assistant | same flags as observer-input assistant | same |
| recall | user :243, toolResult :256, custom_message :124 | `textAndPlaceholders()` with NO options | thinking AND redacted-thinking both become `[non-text content omitted]`; toolCalls stay labeled placeholders |

**Invariant:** Fidelity policy is ROLE-dependent, not global. Observer input is budgeted working material — user/tool-result roles strip to pure text so tokens buy information, not placeholders. Recall is courtroom evidence — every role keeps placeholders so the model can see THAT something non-text existed, and only assistant bodies resurrect reasoning as `[thinking: …]`. Redacted thinking is never rendered anywhere: it is either skipped entirely (assistant bodies) or masked as a generic placeholder (all other recall renders) — "omitted entirely" is therefore true ONLY for assistant bodies, not a dialect-wide property.

## Probe (direct tests)
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
npx vitest run tests/source-serialization-budget.test.ts tests/recall-tool.test.ts
# Executed this pass: 4 + 7 passed. source-serialization-budget.test.ts:75-103 pins the dialect
# contrast end-to-end — the budgeted observer projection truncates a huge tool result to a marked
# excerpt while renderRecallSourceEntry on the SAME entry still contains the full original source
# (:98-102). No unit test pins the literal placeholder strings: textAndPlaceholders sits below
# unit-test granularity (coverage caveat) — pinned by direct read of serialize.ts:27-60 at this pin.
```

## Get live surrounding code
**Retrieve (executed live, resolves all six decisive symbols):**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "textAndPlaceholders textOnly serializeConversation renderRecallMessage renderCustomMessage placeholder thinking toolCall" });
// → textOnly 62-70, serializeConversation 72-96, textAndPlaceholders 27-60,
//   renderCustomMessage 121-139, renderRecallMessage 238-257 (src/serialize.ts)
```

## Verdict
Adopt the two-helper split with an explicit per-role options matrix: keep placeholders wherever a reader must know evidence existed (recall), strip silently where placeholders waste budget (observer input for non-assistant roles), label tool calls with their name+arguments JSON, and treat redacted thinking as never-renderable. Adapt block-type names to your provider's content schema. Omit nothing behavioral — silently converting "omitted" into "placeholder" (or vice versa) changes what the reader believes about the past.
