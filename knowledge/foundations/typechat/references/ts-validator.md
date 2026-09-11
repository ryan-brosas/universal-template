<!-- capsule-v2 -->
# TS validator — how does an in-memory TypeScript compiler validate JSON?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How is JSON type-checked against a .ts schema without emitting code, and how are compiler diagnostics turned into model-repairable messages?

## createTypeScriptJsonValidator
**Path/Symbol:** `typescript/src/ts/validate.ts:62-177` (factory; `validate` :92-121; `flattenDiagnosticMessageText` :126-137; `expandMissingPropertiesMessage` :145-172).
**Signature:** `createTypeScriptJsonValidator<T extends object = object>(schema: string, typeName: string): TypeScriptJsonValidator<T>` where the validator adds `createModuleTextFromJson(jsonObject): Result<string>` and `close(): void`.
**Data Shape:** virtual FS seeded with FOUR files: `/tsconfig.json` (`{strict:true, skipLibCheck:true, noLib:true, types:[]}`, files:[lib.d.ts, schema.ts, json.ts]), `/lib.d.ts` (minimal 9-interface lib :22-30), `/schema.ts` (user schema), `/json.ts` (rewritten per validation). Compiler API loaded synchronously from ESM-only TypeScript 7 via `createRequire(__filename)('typescript/unstable/sync')` (:17-20).

### Decisive source
```ts
writeJsonFile(jsonFileName, moduleResult.data);
const snapshot = api.updateSnapshot({ fileChanges: { changed: [jsonFileName] } });
const programDiagnostics = syntacticDiagnostics.length ? syntacticDiagnostics : program.getSemanticDiagnostics();
...
if (d.code === 2740 && jsonFile && d.fileName === jsonFileName) {
    return expandMissingPropertiesMessage(checker, jsonFile, d.pos) ?? message;
}
```
with per-validate module text (`:174-176`):
```ts
return success(`import { ${typeName} } from './schema';\nconst json: ${typeName} = ${JSON.stringify(jsonObject, undefined, 2)};\n`);
```
**Flow:** stringify JSON into a typed const → mark ONLY /json.ts changed → snapshot update re-typechecks → prefer syntactic over semantic diagnostics → flatten chained messages with indentation → error-2740 special case.
**Invariant:** JSON.stringify output is trusted as TS expression syntax (JSON ⊂ JS literal grammar); the schema file NEVER changes so its check results are cached across validations — only json.ts churns. Error 2740 truncates missing-properties to 4 items ("and N more") which is USELESS as a repair prompt; `expandMissingPropertiesMessage` re-derives the full list via the checker: locate the variable declaration spanning d.pos (using getStart() to exclude trivia), diff target-vs-source property sets excluding SymbolFlags.Optional, and render with NodeBuilderFlags.NoTruncation. Fallback to the original truncated message if the declaration can't be located. `close()` releases the compiler instance but is optional (it doesn't hold the process alive).
**Probe:** `grep -c 'd.code === 2740' typescript/src/ts/validate.ts` (=1); `grep -c 'strict: true' typescript/src/ts/validate.ts` (=1); live pins `typescript/test/validate.test.ts`: :125-173 pins NO "and N more"/" and \d+ more" in any 6+-missing message AND optional `tag` excluded from the list; :97-107 pins single-missing (2741 path unchanged).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typechat", query: "createTypeScriptJsonValidator diagnostics", limit: 5 });
// expandMissingPropertiesMessage surfaces at rank2 under query "stripNulls null properties" too
```

## Verdict
Adopt the write-one-file + changed-file-snapshot pattern for any embed-a-compiler validator; adapt to stable TS APIs when they land (source carries TODO); omit the 2740 expansion only if your host never truncates diagnostics. Direct tests cover valid/invalid/truncation paths at this pin.
