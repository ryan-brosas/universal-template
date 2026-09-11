<!-- capsule-v2 -->
# Sync-only parse/preprocess boundary — how do you convert async-capable language/processor plugins into typed fatal errors at the sync API edge?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do ParserService and ProcessorService normalize plugin results into `{ok:true,...}|{ok:false,errors[]}` while refusing promises?

## ParserService.parseSync
**Path/Symbol:** `lib/services/parser-service.js:ParserService.parseSync` (:32–62).
**Signature:** `parseSync(file: VFile, {language, languageOptions}) → {ok:true, sourceCode} | {ok:false, errors:LintMessage[]}`.
**Data Shape:** error mapping is FIXED: `{ruleId:null, fatal:true, severity:2, message:"Parsing error: "+original, line, column}` — line/column pass through from the language's error object.

### Decisive source
```js
const result = language.parse(file, { languageOptions });
if (typeof result.then === "function")
  throw new Error("Unsupported: Language parser returned a promise.");
if (result.ok) return { ok: true, sourceCode: language.createSourceCode(file, result, { languageOptions }) };
return { ok: false, errors: result.errors.map(error => ({
  ruleId: null, fatal: true, severity: 2,
  message: `Parsing error: ${error.message}`, line: error.line, column: error.column })) };
```

## ProcessorService.preprocessSync / postprocessSync
**Path/Symbol:** `lib/services/processor-service.js:preprocessSync` (:40–83), `postprocessSync` (:93–97).
**Data Shape:** block forms — legacy plain STRING passes through as-is; object blocks become `new VFile(path.join(file.path, `${i}_${block.filename}`), block.text, { physicalPath: file.physicalPath })` (virtual child keeps PHYSICAL parent path). Preprocess exceptions become one fatal message with a stripped `^line \d+:` prefix and `ex.lineNumber`/`ex.column`.

**Flow (both services):** call plugin surface → thenable detection THROWS (sync API cannot await; failing fast beats silent dropped results) → success wraps into ok-true payload → failure maps to the canonical fatal LintMessage shape.
**Invariant:** the "Parsing error:"/"Preprocessing error:" prefixes are part of the output contract (tests pin them) — downstream dedupes/filters on them. Promise rejection is a thrown Error, not an ok:false entry: it signals a BROKEN INTEGRATION (plugin bug), not user-code parse failure. postprocess deliberately does NOT catch — processor bugs propagate.
**Probe:** `tests/lib/services/parser-service.js` (:28–61 parseSync ok paths incl. createSourceCode arg identity :47; :75–99 error shape + "Parsing error: " prefix; :121 line/column preservation; :141 promise-throw). `tests/lib/services/processor-service.js` (:43 VFile objects; :88 legacy string blocks; :106–155 throw-mapping + line-prefix strip + promise-throw; :210 postprocess no-catch).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "ParserService parseSync ProcessorService preprocessSync", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.services.parser-service.ParserService.parseSync" });
```

## Verdict
Adopt the ok-envelope + thenable-refusal pattern for any sync facade over possibly-async third-party surfaces; adapt prefixes to your domain vocabulary.
