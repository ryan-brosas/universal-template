<!-- capsule-v2 -->
# MDX ESM comment gate — how do I catch content that MY tooling accepts but the PRODUCTION consumer rejects?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** JS comments inside MDX ESM blocks pass every local render — how does CI reject them before the docs site's production parser breaks?

## Parse with the consumer's parser, own only your failure class
**Path/Symbol:** `scripts/check-mdx-comments.ts:main` (19–64); header rationale lines 3–5.
**Signature:** `async function main(): Promise<void>` — glob `docs/**/*.mdx`, exit 1 listing `file:line` per offending comment.
**Data Shape:** input = every docs mdx file; detection target = `mdxjsEsm` AST nodes' `data.estree.comments`; output = "OK" or per-location error lines; whole-file parse errors are deliberately OUT of scope (`catch { return [] }`).

### Decisive source
```ts
// Checks for JS comments inside MDX ESM blocks (imports / exports) because they
// break Mintlify's production parser even though they work locally.
const parser = unified().use(remarkParse).use(remarkMdx);
try { tree = parser.parse(content); } catch { return []; } // Parse error -- let other checks catch it
for (const node of tree.children) {
  if (node.type === "mdxjsEsm") {
    const comments = node.data?.estree?.comments || [];
    for (const comment of comments) {
      const line = comment.loc?.start?.line;
      locations.push(line ? `${file}:${line}` : file);
    }
  }
}
```

**Flow:** glob all mdx → parse each with remark-parse + remark-mdx (the SAME parser family as the production MDX consumer, not regex) → walk top-level children for ESM blocks → extract estree comment nodes with source locations → report each as `file:line` and exit 1; a file that fails to PARSE entirely is skipped here because other gates own syntax.
**Invariant:** the gate encodes CONSUMER truth: local acceptance ≠ production acceptance, and each check owns exactly one failure class (comments-in-ESM) while delegating the rest — never widen one gate to swallow another's diagnostics.
**Probe:** `npm run check:docs:js-comments` at HEAD ⇒ "Checking 344 MDX files … OK". RED twin: append `export const trap = 1; /*…*/ // production-parser breaker` to a docs mdx ⇒ "- docs/seps/index.mdx:77" + "JS comments break Mintlify's production MDX parser." + exit 1 (both observed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "check-mdx-comments main", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt consumer-parser gating (validate artifacts with the parser that must ultimately accept them) and single-class gate scoping with explicit delegation for parse failures. Adapt to your CMS/SSG parser pair. Omit Mintlify specifics beyond the rationale. Coverage: no_recorded_issue/metadata_match in the FULL graph (best-effort caveat); no dedicated unit test — npm gate is the probe.
