<!-- capsule-v2 -->
# JS Language declaration — what must a Language plugin object provide so the flat-config linter can lint a new language?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** Which fields and methods form the Language contract, and which side of each responsibility belongs to the language vs the linter?

## The Language object (JS reference implementation)
**Path/Symbol:** `lib/languages/js/index.js` module export (:109–336): static fields (:110–121), `validateLanguageOptions` delegate (`lib/languages/js/validate-language-options.js:153–194`), `normalizeLanguageOptions` (:130–153), `matchesSelectorClass` (:163–229), `parse` (:238–306), `createSourceCode` (:316–335).
**Signature:** `parse(file, {languageOptions}) → {ok:true, ast, parserServices, visitorKeys, scopeManager} | {ok:false, errors:[{message, line, column}]}`; `createSourceCode(file, parseResult, {languageOptions}) → SourceCode`.
**Data Shape:** static surface: fileType:"text", lineStart:1, columnStart:0, nodeTypeKey:"type", visitorKeys; defaultLanguageOptions {sourceType:"module", ecmaVersion:"latest", parser:espree, parserOptions:{}}.

### Decisive source
```js
// parse() NEVER throws — parse errors are problems, not exceptions:
try {
  const parseResult = typeof parser.parseForESLint === "function"
    ? parser.parseForESLint(textToParse, parserOptions)
    : { ast: parser.parse(textToParse, parserOptions) };
  return { ok: true, ast, parserServices: parseResult.services ?? {}, ... };
} catch (ex) {
  const message = ex.message.replace(/^line \d+:/iu, "").trim();
  return { ok: false, errors: [{ message, line: ex.lineNumber, column: ex.column }] };
}
// createSourceCode(): parser-supplied scopeManager wins, else analyze here:
const scopeManager = parseResult.scopeManager || analyzeScope(ast, languageOptions, visitorKeys);
```

**Flow:** Config resolves the language string to this object → linter calls validateLanguageOptions at config time (ajv-style grammar over ecmaVersion/sourceType/parser) → normalizeLanguageOptions rewrites ecmaVersion "latest"/ES3/ES5 forms into year numbers and, when the parser IS espree, pushes sourceType down into parserOptions (clearing globalReturn under modules) → parse per file (shebang pre-rewritten to //comment; parserOptions forced to loc/range/tokens/comment/eslintVisitorKeys/eslintScopeManager/filePath) → createSourceCode runs scope analysis lazily and wraps everything in SourceCode.
**Invariant:** the ok-envelope is the language-side error boundary — throwing from parse would crash verify instead of producing a fatal LintMessage. esquery pseudo-classes for custom taxonomies are a LANGUAGE responsibility: matchesSelectorClass implements statement/declaration/pattern/expression/function via type-SUFFIX fallthrough chains (Statement→Declaration, Pattern→Expression, Identifier counts as expression unless child of MetaProperty) and throws on unknown class names.
**Probe:** no dedicated suite exists at pin — `tests/lib/languages/js/index.js` is absent (coverage caveat). Behavior is pinned indirectly by `tests/lib/linter/linter.js:11093` ("Invalid ecmaVersion" surfaced as a fatal message) plus the whole-linter integration surface. Executed at pin: mocha tests/lib/config/config.js subset 31 passing covers the Config-side binding that consumes these hooks.
**Coverage caveat:** parse()/createSourceCode()/matchesSelectorClass() claims rest on direct source reads + indirect linter pins, not a direct unit test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "JavaScript Language parse createSourceCode normalizeLanguageOptions matchesSelectorClass", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.languages.js.createSourceCode" });
```

## Verdict
Adopt the contract shape: static descriptor fields + options validation hook + options normalization hook + non-throwing ok-envelope parse + deferred scope analysis in createSourceCode. Adapt the JS-specific espree pushing and shebang rewriting to host languages; omit matchesSelectorClass if the host never extends esquery classes.
