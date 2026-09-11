<!-- capsule-v2 -->
# WASM grammar loader — How do you lazy-load per-extension parsers without re-initializing or mis-keying the parser map?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory project `Roo-Code`. **Question:** When several extensions share one grammar (and one grammar serves a template language), how must the parser map be keyed so lookups by file extension always hit — and what breaks silently when they don't?

## Connected graph-selected seam
**Path/Symbol:** `src/services/tree-sitter/languageParser.ts:loadRequiredLanguageParsers` (:78-231); `loadLanguage` (:40-51); module init flag `isParserInitialized` (:53, :81-89).
**Signature:** `async function loadRequiredLanguageParsers(filesToParse: string[], sourceDirectory?: string): Promise<LanguageParser>` where `LanguageParser = { [ext: string]: { parser: Parser; query: Query } }`.
**Data Shape:** Input: list of file paths → unique lowercase extensions (`.slice(1)`, :91). Output: map keyed BY EXTENSION STRING (`js`, `py`, `erb`, …), each holding an initialized `web-tree-sitter` Parser (its language set) plus a compiled Query built from the repo's own query-pack string for that language. WASM binaries resolve from `sourceDirectory || __dirname` as `tree-sitter-<lang>.wasm`.

### Decisive source
```ts
case "js":
case "jsx":
case "json":
	language = await loadLanguage("javascript", sourceDirectory)
	query = new Query(language, javascriptQuery)
	break
// ...
case "ejs":
case "erb":
	parserKey = "embedded_template" // Use same key for both extensions.
	language = await loadLanguage("embedded_template", sourceDirectory)
	query = new Query(language, embeddedTemplateQuery)
	break
```

**Flow:** one-time `Parser.init()` guarded by the module flag (:81-89) → derive unique extensions from the requested files → per extension: switch maps ext → (grammar wasm, query string, optional remapped key) → build `new Parser()` + `setLanguage(language)` and store under the key → return. Extension families sharing one grammar: `js/jsx/json→javascript`, `cpp/hpp→cpp`, `c/h→c`, `cs→c_sharp`, `ml/mli→ocaml`, `kt/kts→kotlin`, `ex/exs→elixir`; special remap `ejs/erb→embedded_template` sets `parserKey="embedded_template"`.

**Invariant:** THE KEYING TRAP: the production consumer looks up `languageParsers[extLang]` using the FILE'S EXTENSION (`src/services/tree-sitter/index.ts:309`) — but for `.ejs` files the loader stored the entry under `"embedded_template"`, not `"ejs"` (only `.erb` coincides with its extension). So in production a `.ejs` file resolves `undefined` → `{}` destructure → `parseFile` returns `"Unsupported file type: <path>"` (:311). The spec suite cannot catch this because `__tests__/helpers.ts:96` keys its mock map by `extKey` and `parseSourceCodeDefinitions.embedded_template.spec.ts` uses `extKey:"erb"` + `test.erb`. A porter who "fixes" the asymmetry by changing only the lookup side breaks `.erb` instead — the correct port stores BOTH keys (`parsers["ejs"] = parsers["erb"] = …`). Secondary invariant: the init flag makes `Parser.init()` idempotent across calls (cheap repeated loads are safe); unsupported extensions throw loudly (`Unsupported language: ${ext}`, :222) rather than returning a null entry. Known accepted wart: `.scala` deliberately loads the LUA query until a Scala grammar lands (:176 comment) — outline quality for `.scala` is knowingly wrong-shaped, not broken.

**Probe:** `src/services/tree-sitter/__tests__/languageParser.spec.ts` against real wasms from `node_modules/tree-sitter-wasms/out`: `parsers.py/.js/.jsx/.rs/.go/.c/.h/.cpp/.hpp/.kt/.kts` all defined with `.query` present (extension-keyed shape pinned for every family EXCEPT ejs/erb, whose coverage gap is exactly the trap above).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "loadRequiredLanguageParsers", limit: 5 });
// → Roo-Code.src.services.tree-sitter.languageParser.loadRequiredLanguageParsers Function src/services/tree-sitter/languageParser.ts 78-231
```

## Verdict
Adopt: unique-ext fan-out over the requested file set, shared-grammar case grouping, one-time `Parser.init()`, and loud failure on unknown extensions. Adapt the wasm source directory to your bundler (`__dirname` vs packaged assets). Omit nothing structural — but when you port the template-language remap, store BOTH extension keys or your consumers' `[extLang]` lookups silently miss. Live-defect caveat recorded honestly: the `.ejs` half of the remap is untested and broken-by-keying at this pin; the capsule documents intended behavior AND actual behavior so a porter chooses deliberately.
