<!-- capsule-v2 -->
# Definition query-pack grammar — How do tree-sitter query captures encode "definition" so a language-agnostic walker can outline any file?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory project `Roo-Code`. **Question:** What capture-name convention must every per-language S-expression query follow so ONE downstream processor can build outlines for ~40 languages without per-language code?

## Connected graph-selected seam
**Path/Symbol:** `src/services/tree-sitter/queries/typescript.ts` (whole file, 123L; representative of `queries/{javascript,tsx,python,rust,go,c,cpp,c-sharp,ruby,java,php,html,swift,kotlin,css,ocaml,solidity,toml,vue,lua,systemrdl,tlaplus,zig,embedded_template,elisp,elixir}.ts`); re-export hub `src/services/tree-sitter/queries/index.ts`; consumer contract in `src/services/tree-sitter/index.ts:215`.
**Signature:** Each module default-exports one S-expression string; patterns pair an anonymous wrapper capture with a name capture: `(node_type ... (child) @name.definition.kind) @definition.kind`.
**Data Shape:** Two capture roles per pattern: `@definition.<kind>` on the FULL node (carries start/end rows used as the outline range) and `@name.definition.<kind>` on the identifier child (resolves to `.parent` = full node downstream). Kinds seen: function, method, class, module, lambda, switch, test.

### Decisive source
```lisp
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(call_expression
  function: (identifier) @func_name
  arguments: (arguments
    (string) @name
    [(arrow_function) (function_expression)]) @definition.test)
  (#match? @func_name "^(describe|test|it)$")

(arrow_function) @definition.lambda

(switch_statement) @definition.switch
```

**Flow:** grammar parses source → compiled Query runs over `tree.rootNode` → captures stream into `processCaptures`, which keeps only names containing `definition`/`name`. Patterns come in three flavors: named-definition pairs (function/method/class/module — both captures, parent resolution), bare node captures (`@definition.lambda`, `@definition.switch` — no name needed), and predicate-gated semantic captures (`#match? @func_name "^(describe|it)$"` + string-argument shape → test blocks become outline entries). Queries are adapted from tree-sitter's stock tag queries with captures pruned to definitions only (:157 comment in index.ts).

**Invariant:** The convention IS the interface: (a) every range-bearing capture MUST be named `@definition.*` or its name-partner `@name.definition.*` — anything else is silently dropped by the name filter, so a new pattern that forgets the prefix produces zero outline lines with no error; (b) name-captures REQUIRE the wrapped-node structure `(… ) @definition.x` so `node.parent` resolves — a bare `@name.definition.function` on an identifier without a wrapping capture yields `parent` pointing at whatever encloses it and can emit the WRONG span; (c) predicates like `#match?` run inside tree-sitter at query time — filtering happens before your code sees captures, so porting the predicate into post-processing changes which captures exist but must preserve identical output; (d) queries are plain strings compiled once per language by the loader — they are DATA, safe to vendor, but must match the grammar's node type names exactly (a renamed grammar field fails silently to zero captures).

**Probe:** `src/services/tree-sitter/__tests__/parseSourceCodeDefinitions.javascript.spec.ts` pins end-to-end behavior through real wasm+query: function/generator/async declarations, classes, methods, getters/setters, object-literal members, arrows, decorators each match `\d+--\d+ \| <source line>`; per-language twins cover every other grammar in the pack.

## Get live surrounding code
**Retrieve:**
```ts
// Query packs are default-exported STRING DATA (src/services/tree-sitter/queries/*.ts),
// not graph symbols — retrieve via the consuming walker instead:
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "processCaptures", limit: 5 });
// → Roo-Code.src.services.tree-sitter.processCaptures Function src/services/tree-sitter/index.ts 184-284
```

## Verdict
Adopt the capture vocabulary verbatim (`@definition.<kind>` + `@name.definition.<kind>` pairs, bare `@definition.*` for unnamed spans, `#match?` predicates for semantic kinds) whenever you build a definition-outline walker — it is what lets one 100-line processor serve every language. Adapt pattern sets per grammar version; keep them in data files, not code. Omit GitHub's original tag-query surface (usages/references) — this fork deliberately prunes to definitions only.
