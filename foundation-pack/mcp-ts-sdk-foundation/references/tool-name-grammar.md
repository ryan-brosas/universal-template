<!-- capsule-v2 -->
# SEP-986 tool-name grammar — what makes a tool name valid, and which violations are warnings rather than rejections?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should a server validate registered tool names without over-rejecting names the spec merely discourages?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/toolNameValidation.ts` (whole, 116L): `TOOL_NAME_REGEX = /^[A-Za-z0-9._-]{1,128}$/` (:16), `validateToolName` (:24+).
**Signature:** `validateToolName(name: string): { isValid: boolean; warnings: string[] }`.
**Data Shape:** HARD rules: 1–128 chars; case-sensitive; only `A-Z a-z 0-9 _ - .`. SOFT rules (warnings, not failures): spaces/commas anywhere; leading/trailing dash or dot.

### Decisive source
```ts
if (!TOOL_NAME_REGEX.test(name)) {
    const invalidChars = [...name]
        .filter(char => !/[A-Za-z0-9._-]/.test(char))
        .filter((char, index, arr) => arr.indexOf(char) === index); // dedupe
    warnings.push(`Tool name contains invalid characters: ${invalidChars.map(c => `"${c}"`).join(', ')}`, …);
}
```

**Flow:** registration-time validation → hard violations set `isValid:false` with actionable diagnostics (deduped offending-character list) → soft violations accumulate warnings without blocking → hosts decide whether warnings surface to authors.

**Invariant:** The two-tier split mirrors the SEP's SHOULD/MUST asymmetry: length/charset are enforceable grammar; leading-dash/dot are portability hazards only. Diagnostics name the exact invalid characters instead of a bare boolean — author-facing validation errors should be self-explanatory.

**Probe:** deterministic source pin (whole 116L file read at HEAD); upstream test suite for this module was not present at this pin — in-capsule coverage caveat recorded.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateToolName TOOL_NAME_REGEX", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the MUST/SHOULD split and character-level diagnostics; adapt limits to your registry's constraints; omit if your platform owns naming upstream of the SDK.
