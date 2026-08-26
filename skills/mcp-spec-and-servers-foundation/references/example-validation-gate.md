<!-- capsule-v2 -->
# Example validation gate — how do I validate protocol example fixtures against the exact published schema without duplicating dialect logic?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** Where do example payloads live, what makes their directory name load-bearing, and how does the validator pick the right JSON Schema dialect per version?

## Dialect-sniffed Ajv validation keyed by directory-name-as-type
**Path/Symbol:** `scripts/validate-examples.ts:validateSchemaExamples` (31–84) with `validateExample` (15–29) and `main` (86–118).
**Signature:** `async function validateSchemaExamples(schemaDir: string): Promise<ValidationResult[]>` where `ValidationResult = [name: string, errors: Promise<string[]>]`.
**Data Shape:** reads `schema/<v>/schema.json`; fixtures at `schema/<v>/examples/<TypeName>/*.json`; compile unit `{ $schema, [defsKey]: entireDefsMap, ...typeDef }`; returns per-file error-string arrays; aggregate "Results: P passed, F failed" + exit 1 on any failure.

### Decisive source
```ts
const is2020 = (schema.$schema as string).includes("2020-12");
const ajv = is2020 ? new Ajv2020({ allErrors: true, strict: false }) : new Ajv({ allErrors: true, strict: false });
addFormats(ajv);
const defsKey = is2020 ? "$defs" : "definitions";
// ...
let validate: ValidateFunction | undefined;
if (defs?.[typeName]) {
  validate = ajv.compile({ $schema: schema.$schema, [defsKey]: schema[defsKey], ...(defs?.[typeName] as object) });
}
// unknown type name ⇒ every file under it errors:
results.push([examplePath, Promise.resolve([`Type "${typeName}" not found in schema`])]);
```

**Flow:** discover every `schema/*/` version dir → parse its generated schema.json → SNIFF dialect from the artifact's own `$schema` URL (never a hardcoded version list — stays correct when versions are added) → for each `examples/<TypeName>/` dir compile ONE validator embedding the whole defs map plus the named type's def spread top-level so internal `#/$defs/…` refs resolve → validate each `.json`, collect `instancePath: message` lines → parallel across versions, exit 1 if any failed.
**Invariant:** failure asymmetry is deliberate — UNKNOWN fixture type names fail closed ("Type … not found in schema", observed exit 1), while an absent `examples/` dir fails open via `catch { return [] }` (optional plane; only draft and 2026-07-28 carry examples on disk — 88 types / 129 files each); JSON.parse errors become that file's error entry rather than crashing the batch.
**Probe:** `npm run check:schema:examples` at HEAD ⇒ "Results: 258 passed, 0 failed". RED twin: add `examples/BogusTypeName/bad.json` ⇒ "✗ …/BogusTypeName/bad.json · Type "BogusTypeName" not found in schema · Results: 258 passed, 1 failed" + exit 1 (both observed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "validateSchemaExamples", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fixture-validation keyed by convention with fail-closed unknown keys, fail-open optional planes, and dialect sniffing from the artifact's own metadata so downstream consumers stay in lockstep with the generator's transform. Adapt Ajv options and the directory grammar to your layout. Omit MCP-specific type coverage. Coverage: no_recorded_issue/metadata_match in the FULL graph (best-effort caveat); no dedicated unit test — npm gate is the probe.
