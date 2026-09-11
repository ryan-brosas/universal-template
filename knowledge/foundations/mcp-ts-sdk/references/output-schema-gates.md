<!-- capsule-v2 -->
# Output-schema validation gates — when is structuredContent required, and why must the presence check be `=== undefined`?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A tool declares an `outputSchema` — exactly which handler returns must fail validation, and which legal values must NOT?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/mcp.ts`: `validateToolOutput` (:288-322), input-required early-out (:295-297), `=== undefined` presence rule + comment (:303-312), tools/call catch-all (:230-235).
**Signature:** `validateToolOutput(tool, result: CallToolResult | InputRequiredResult, toolName): Promise<void>`.
**Data Shape:** `structuredContent` may legally be any JSON value incl. `null`, `0`, `false`, `""`.

### Decisive source
```ts
// An input-required result is not the tool's final output: structured content is
// only required (and validated) on the completing result.
if (isInputRequiredResult(result)) return;
if (result.isError) return;

// SEP-2106: `structuredContent` may legally be any JSON value including `null`, `0`,
// `false`, `""`. The presence check is therefore `=== undefined` (not falsy); when
// present, the value is ALWAYS validated against the output schema — a falsy value
// against an object-typed schema fails validation, so this is not a guard weakening.
if (result.structuredContent === undefined) {
    throw new ProtocolError(ProtocolErrorCode.InvalidParams,
        `Output validation error: Tool ${toolName} has an output schema but no structured content was provided`);
}
```

**Flow:** no outputSchema ⇒ no checks → input-required ⇒ skip (not final output) → isError ⇒ skip → missing structuredContent ⇒ InvalidParams throw → validate against schema; failure also throws. Errors thrown by input validation/handler execution are converted to `{content:[{type:'text',text:msg}], isError:true}` by the catch-all — EXCEPT `UrlElicitationRequired` ProtocolErrors, which are rethrown unwrapped so the seam above can era-route them.

**Invariant:** Falsy-but-present values MUST reach the validator (a falsy check would silently pass `structuredContent: null` on an object-typed schema). Validation runs on the COMPLETING round only. The catch-all conversion has exactly one escape hatch — get it wrong and multi-round-trip signaling dies as an isError string.

**Probe:** `test/integration/test/server/mcp.test.ts` (output-validation failures surface as protocol errors); `inputRequired.test.ts` :120/:192 (input_required passes through unvalidated); completer cap pinned in `test/e2e/scenarios/completion.test.ts` :246-252 (`values ≤ 100`, `total = values.length`, `hasMore` false under cap).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateToolOutput structuredContent normalizeContentlessToolResult createToolError", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt `=== undefined` presence semantics for any-JSON fields + completing-round-only validation + single-escape-hatch error conversion; adapt error codes; omit SEP-2106 wire-projection details (`tools-call-validation-funnel.md` owns them).
