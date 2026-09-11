<!-- capsule-v2 -->
# UI message validation ladder — which fields does structural validation check, when does it deliberately NOT re-validate tool input, and why can terminal calls survive a missing tool schema?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you validate untrusted client-submitted UIMessage history against typed tools without crashing replays of already-terminal (or schema-lost) tool calls?

## safeValidateUIMessages / validateUIMessages
**Path/Symbol:** `packages/ai/src/ui/validate-ui-messages.ts` whole file (584L): `uiMessagesSchema` (:29-365, lazy), per-message `.superRefine` empty-parts rule (:349-361), `.nonempty` array rule (:363), `safeValidateUIMessages` (:382-545), thin throwing wrapper `validateUIMessages` (:554-584).
**Signature:** `safeValidateUIMessages({messages: unknown, metadataSchema?, dataSchemas?, tools?}): Promise<{success:true,data}|{success:false,error}>`; `validateUIMessages(...): Promise<UIMessage[]>` (throws).

### Decisive source
```ts
// :468-498 — unknown tool name: TERMINAL states skip, non-terminal throws.
if (tools && part.type.startsWith('tool-')) {
  const toolName = toolPart.type.slice(5);
  const tool = getOwn(tools, toolName);              // own-property read
  if (!tool && (state === 'output-available' || state === 'output-error'
             || state === 'output-denied')) continue; // tolerate history drift
  if (!tool) return { success:false, error: new TypeValidationError({
      value: toolPart.input,
      cause: `No tool schema found for tool part ${toolName}`, ...}) };
}
// :501-503 — the comment IS the invariant:
// Note: input is intentionally not re-validated for terminal states.
// Terminal tool calls can keep invalid or incomplete input, and
// re-validating it on replay would crash follow-up messages.
if (toolPart.state === 'input-available') { /* validate input */ }
if (toolPart.state === 'output-available' && tool.outputSchema) { /* validate output */ }
```

**Flow:** null/undefined messages ⇒ `InvalidArgumentError` BEFORE any schema run → structural pass: role enum + part-type union mirrors ui-messages.ts exactly (dynamic-tool and tool-* each spelled out in all 7 states with `z.never()` on impossible fields; `output-error` allows optional `input` + `rawInput`) → assistant parts may be empty; NON-assistant empty parts ⇒ issue at path `[i].parts` → metadata validated per-message ONLY if `metadataSchema` given (context field `messages[i].metadata`, entityId = message.id) → data parts (`data-` prefix, name = `type.slice(5)`) REQUIRE a registered schema — missing one is an ERROR (unlike tools!) → tool input validated only in `input-available`; tool OUTPUT validated in `output-available` when `tool.outputSchema` exists; `input-streaming` never input-validated. All failures carry precise context (`messages[i].parts[j].input`, entityName, toolCallId).
**Invariant:** validation strictness DECREASES with state age: streaming inputs are incomplete by design, terminal results are historical facts — re-validating them on replay would make one stale payload brick every subsequent turn, so terminal states skip input checks entirely AND tolerate vanished tool schemas (provider-executed or removed tools must still render). The asymmetry to port carefully: missing DATA schema is fatal, missing TOOL schema is fatal only for pre-terminal states. Empty-parts rule is asymmetric too (assistant-only exempt). Use `getOwn`-style own-property lookup for tool names.

**Probe:** `bash -c "grep -n \"should not re-validate tool input when state is output-available\\|should throw error when no tool schema is found\\|should skip validation for tool part in output-denied state\" $REFERENCE_ROOT/ai/packages/ai/src/ui/validate-ui-messages.test.ts"` → lines 1145, 1430, 1514.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "validateUIMessages safeValidateUIMessages uiMessagesSchema", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-tier ladder (structural union → optional metadata/data schemas → tool input/output gated BY STATE) with the terminal-state lenience comment as a named invariant. Adapt error taxonomy; keep the data-vs-tool missing-schema asymmetry deliberate. Omit the zod-specific superRefine shape only if your validator expresses equivalent path-context errors.
