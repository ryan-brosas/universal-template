<!-- capsule-v2 -->
# Tool-call parse & repair ladder — how does a raw model tool call become a validated typed call, and what exactly happens on each failure?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** When a provider returns a malformed, unknown, or schema-violating tool call, what is the exact cause-chain (parse → repair → degrade) and which error types trigger repair?

## parseToolCall three-ring try/catch
**Path/Symbol:** `packages/ai/src/generate-text/parse-tool-call.ts:19-116` (`parseToolCall`), helpers at `:118-135` (`refineParsedToolCallInput`), `:137-162` (`parseProviderExecutedDynamicToolCall`), `:164-226` (`doParseToolCall`).
**Signature:** `parseToolCall({toolCall: LanguageModelV4ToolCall, tools?, repairToolCall?, refineToolInput?, instructions?, messages}): Promise<TypedToolCall<TOOLS>>`.
**Data Shape:** In: raw wire tool call `{toolName, toolCallId, input: string, providerExecuted?, dynamic?}` + ToolSet keyed by name. Out: typed call with parsed+schema-validated `input` object, `title`, optional `toolMetadata` from the tool's own `metadata` field; OR a degraded invalid call.

### Decisive source
```ts
// ring 2 catch — ONLY these two error classes are repairable:
} catch (error) {
  if (
    repairToolCall == null ||
    !(
      NoSuchToolError.isInstance(error) ||
      InvalidToolInputError.isInstance(error)
    )
  ) {
    throw error;
  }
  let repairedToolCall: LanguageModelV4ToolCall | null = null;
  try {
    repairedToolCall = await repairToolCall({
      toolCall, tools,
      inputSchema: async ({ toolName }) =>
        (await asSchema(getOwn(tools, toolName)?.inputSchema).jsonSchema),
      instructions, system: instructions, // system = deprecated alias of instructions
      messages, error,
    });
  } catch (repairError) {
    throw new ToolCallRepairError({ cause: repairError, originalError: error });
  }
  if (repairedToolCall == null) throw error; // null repair ⇒ ORIGINAL error rethrown
  return await refineParsedToolCallInput({
    toolCall: await doParseToolCall({ toolCall: repairedToolCall, tools }),
    refineToolInput,
  });
}
```

**Flow:** Ring 1: no tools at all → provider-executed dynamic calls still parse via `parseProviderExecutedDynamicToolCall` (empty-string input short-circuits to `{}`, never JSON-parsed), everything else → `NoSuchToolError`. Ring 1.5: `doParseToolCall` resolves the tool with **prototype-safe `getOwn`** (inherited names like `constructor` must not match), missing → `NoSuchToolError` carrying `availableTools: Object.keys(tools)`; empty/whitespace input → validate `{}` against the schema instead of parsing (many models emit `""` for no-arg calls); otherwise `safeParseJSON(text, schema)`; failure → `InvalidToolInputError {toolName, toolInput, cause}`. After ANY successful parse, `refineParsedToolCallInput` looks up `getOwn(refineToolInput, toolName)` — absent ⇒ return unchanged. Ring 2: repair engages only for `NoSuchToolError | InvalidToolInputError`; the repaired wire call is RE-PARSED through the full `doParseToolCall` (repair output is unvalidated text until it passes schema again). Ring 3: any surviving error degrades to an invalid tool-call part — `input` is best-effort `safeParseJSON` value when parseable else the RAW string, plus `dynamic: true, invalid: true, error` and preserved `providerMetadata`.

**Invariant:** `parseToolCall` NEVER throws out of ring 3 — every terminal failure becomes a visible `{invalid: true}` part so downstream history keeps one entry per wire tool call (no dangling references); repair returning `null` means "cannot help", NOT a new error — the original error surfaces (test pins this snapshot).

**Probe:** `packages/ai/src/generate-text/parse-tool-call.test.ts:472` ("should re-throw error if tool call repair returns null" — result is the invalid part with original `AI_InvalidToolInputError` in `error`, `dynamic:true, invalid:true`); also `:375` (repair invoked once with `instructions` AND deprecated-alias `system` both set), `:83` (inherited property name collision must not create a refinement), `:258/:288` NoSuchToolError shapes, `:805` metadata survives onto invalid parts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "parseToolCall doParseToolCall InvalidToolInputError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-ring ladder: strict two-error repair gate, re-parse-after-repair, null-repair-rethrows-original, always-degrade-to-visible-part, prototype-safe tool/refinement lookup, empty-input→`{}` validation. Adapt the error taxonomy names and the `system`→`instructions` deprecation aliasing to your host. Omit the V4 wire type specifics.
