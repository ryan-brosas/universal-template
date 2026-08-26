<!-- capsule-v2 -->
# Edit-input widening — how do you accept both array and single-object edits without a breaking schema change?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c` (drift-window addition to tools/edit.ts). Codebase Memory `pi-upstream`. **Question:** A porter's edit tool schema requires `edits: [{oldText,newText},...]` but models keep sending a bare `{oldText,newText}` — where is the coercion applied and why there?

## prepareEditArguments: widen single-edit shapes into the array before validation
**Path/Symbol:** `packages/agent/src/harness/tools/edit.ts:41-47` (`isSingleEditInput` type guard), `:58-70` (`prepareEditArguments` coercion), legacy alias handling follows at :71+.
**Signature:** `function isSingleEditInput(value: unknown): value is { oldText: string; newText: string }` (object, not array, both fields typeof string); `prepareEditArguments(input): EditToolInput`.
**Data Shape:** Accepted input forms after normalization: `{edits: [{oldText,newText},...]}`, `{edits: "[{...}]"}` (JSON string → parsed array OR parsed single object), `{edits: {oldText,newText}}` (single object), plus legacy top-level `{oldText,newText}`.

### Decisive source
```ts
if (typeof args.edits === "string") {
    try {
        const parsed: unknown = JSON.parse(args.edits);
        if (Array.isArray(parsed)) {
            args.edits = parsed;
        } else if (isSingleEditInput(parsed)) {
            args.edits = [parsed];
        }
    } catch {}
} else if (isSingleEditInput(args.edits)) {
    args.edits = [args.edits];
}
```

**Flow:** raw tool args → string form JSON-parsed with silent catch (parse failure falls through to later legacy/error paths) → parsed array kept, parsed single object wrapped into one-element array → non-string single object also wrapped → only then does strict schema validation see a canonical array. The guard deliberately REJECTS arrays (`Array.isArray` check first) so an array input never double-wraps.
**Invariant:** Coercion happens in the ARGUMENT-PREPARATION layer, not the schema and not the executor: the declared schema stays strict (arrays only) so the model-facing contract doesn't loosen, while real-world single-edit invocations still succeed. Silent `catch {}` on the string path means malformed JSON degrades to the legacy-compat path rather than a parse error surfacing from deep inside.
**Probe:** Deterministic source probes from repo root at this pin: `grep -c "isSingleEditInput" packages/agent/src/harness/tools/edit.ts` (3: guard def + two uses at :63/:67) and `grep -n "args.edits = \[parsed\]" packages/agent/src/harness/tools/edit.ts` (1 hit). Coverage caveat: dedicated unit test for the single-object branch not located upstream at this pin; edit-tool tests cover the array path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "prepareEditArguments edits single oldText newText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt argument-layer widening: keep the published tool schema strict, coerce observed single-item shapes (direct or inside JSON strings) into arrays before validation. Adapt accepted aliases to your model population's actual error modes. Omit if your tool inputs come from a typed SDK that already guarantees shape. Coverage caveat: single-object branch pinned by source citation + greps; no direct unit test located at this pin.
