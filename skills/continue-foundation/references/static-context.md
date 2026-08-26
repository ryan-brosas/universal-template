<!-- capsule-v2 -->
# Static contextualization — tree-sitter type-graph analysis that injects relevant type/header snippets

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue's experimental static-context feature (enabled via `experimental.enableStaticContextualization`) analyze the type graph around the cursor and inject relevant type/header snippets into the FIM prompt?

## The static context service
**Path/Symbol:** `core/autocomplete/context/static-context/StaticContextService.ts` (whole, 879L).
**Signature:** `class StaticContextService` with `getContext(helper): Promise<AutocompleteStaticSnippet[]>`; private `getHoleContext`, `extractRelevantTypes`, `extractRelevantHeaders`, `generateTargetTypes`, `normalize`, `isTypeEquivalent`.
**Data Shape:** returns `AutocompleteStaticSnippet[]` — one for the hole's full hover result, one per relevant-type file, one per relevant-header file.

### Decisive source
```ts
// getHoleContext: inject "@;" at the cursor to force a tree-sitter ERROR node (the "hole")
const injectedContent = this.insertAtPosition(sketchFileContent, cursorPosition, "@;");
const ast = await getAst(sketchFilePath, injectedContent);
const query = await getQueryForFile(sketchFilePath, `static-context-queries/hole-queries/${language}.scm`);
const captures = query.captures(ast.rootNode);
// captures: function.decl -> fullHoverResult; function.name; function.params -> paramsTypes; function.type -> functionTypeSpan
if (res.functionTypeSpan === "") { res.functionTypeSpan = `${paramsTypes} => any`; res.returnTypeIsAny = true; }
```

**Flow:** `getContext` scans the workspace for `.ts` files (skipping node_modules/.git/dist/build/out/.next/coverage/.nyc_output/tmp/temp/.cache and dot-dirs), then: (1) `getHoleContext` injects `@;` at the cursor to create a tree-sitter error node and runs a per-language hole query to extract the enclosing function's decl/name/params/type; (2) `extractRelevantTypes` recursively resolves type identifiers via `ide.gotoTypeDefinition`, reads the target file, finds the enclosing type declaration, and recurses — building a map of identifier→type-span+source; (3) `extractRelevantHeaders` scans top-level decls of all TS files, builds a type span for each (`extractFunctionTypeFromDecl` or signature-help fallback with arrow-type conversion), and keeps those whose normalized type is equivalent to a target type; (4) `generateTargetTypes` + `normalize` compare types by reducing function/tuple/union/type-identifier/predefined nodes to a canonical normal form (recursively inlining aliases). The result is assembled into snippets keyed by filepath.

**Invariant:** the "hole" is created by injecting `@;` at the cursor to force a tree-sitter error node — the whole feature depends on this; type equivalence is decided by a hand-written `normalize` that inlines type aliases and canonicalizes function/tuple/union shapes (TypeScript "sucks" — sets of objects accumulate duplicates, so a `Map<string, ...>` keyed by `JSON.stringify` is used for dedup); `returnTypeIsAny` short-circuits header extraction.

**Probe:** no direct vitest for StaticContextService (feature is experimental, gated behind `experimental.enableStaticContextualization`). Coverage caveat: no direct test file — the seam is source-grounded; the `@;` hole-injection and tree-sitter query contract are the decisive behaviors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "StaticContextService getHoleContext extractRelevantTypes normalize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `@;` hole-injection trick, the recursive type-definition resolution, the normal-form type equivalence, and the filepath-keyed snippet assembly; adapt the tree-sitter query paths and language support to host; omit the experimental gating and the TS-only file scan unless a target needs it. Coverage caveat: no direct test — source-grounded only.
