<!-- capsule-v2 -->
# Markdown frontmatter grammar — how does rule text get its identity and glob scope without ever failing a load?

**Source:** Continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What is the exact frontmatter contract for markdown-authored rules (name, globs, invokable), and what happens when the YAML between the `---` fences is garbage?

## Fail-open frontmatter split with directory-scoped glob anchoring
**Path/Symbol:** `packages/config-yaml/src/markdown/markdownToRule.ts` (whole file, 115 lines): `RuleFrontmatter` (:8–15), `parseMarkdownRule` (:20–49), `getRuleName` (:51–71), `getGlobPattern` (:73–96), `markdownToRule` (:98–115).
**Signature:** `parseMarkdownRule(content: string): { frontmatter: RuleFrontmatter; markdown: string }`; `markdownToRule(rule: string, id: PackageIdentifier, relativePathForGlobs?: string): RuleObject`.
**Data Shape:** `RuleFrontmatter = { globs?, regex?, name?, description?, alwaysApply?, invokable? }` — all optional, passed through verbatim (no defaults injected here; loaders add e.g. `alwaysApply: true` for agent files).

### Decisive source
```ts
const parts = normalizedContent.split(/^---\s*$/m);
if (parts.length >= 3) {
  // Join the remaining parts back together (in case there are more --- in the markdown)
  const markdownContent = parts.slice(2).join("---");
  try {
    const frontmatter = YAML.parse(frontmatterStr) || {}; // Handle empty frontmatter
    return { frontmatter, markdown: markdownContent.trim() };
  } catch (e) {
    console.warn("Error parsing markdown frontmatter:", e);
    return { frontmatter: {}, markdown: normalizedContent }; // ENTIRE content becomes the rule
  }
}
```

**Flow:** CRLF-normalize → split on horizontal rules `/^---\s*$/m` → ≥3 parts ⇒ parse part[1] as YAML (`|| {}` tolerates empty frontmatter); body = everything after the SECOND fence re-joined on `"---"` so later horizontal rules in the doc survive. YAML PARSE ERROR ⇒ warn + treat the ENTIRE content as body with empty frontmatter — never throws. Name ladder: frontmatter.name > last TWO path segments joined `"/"` (file ids) > package display name (slug ids). Glob anchoring (`getGlobPattern`): skipped when `relativeDir` is undefined OR includes `".continue"`; non-`**` globs anchored as `dir + "**/" + glob`, `**`-prefixed globs just prefixed; MISSING globs outside `.continue` ⇒ `dir + "**/*"` (dir-local by default).
**Invariant:** rule markdown can never fatally break a config load — every parse failure degrades to "whole file is the rule". The `.continue` exclusion prevents double-anchoring rules that already carry repo-rooted globs.
**Probe:** no dedicated suite at this pin (recorded caveat); grammar consumers are pinned by the loaders' suites cited in `markdown-rules-source-plane.md`. Source-pinned observables: `"a\n---\nbad: [yaml\n---\nbody"` returns `{frontmatter:{}, markdown:"a\n---\nbad: [yaml\n---\nbody"}`; `getGlobPattern(undefined, "src/")` ⇒ `"src/**/*"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "parseMarkdownRule frontmatter rule name glob pattern", limit: 10, fields: ["signature", "lines"] });
// BM25 returned all five symbols of this file exactly; check_index_coverage => no_recorded_issue.
```

## Verdict
Adopt the fail-open split-and-degrade parser, the body-rejoin so `---` inside docs survives, the two-segment file-id naming, and dir-scoped default globbing with the dot-dir exclusion; adapt the frontmatter key set to your rule schema; omit the package-display-name branch if you have no hub packages. Trap: because parse errors are swallowed to `{}`, a typo'd frontmatter silently publishes the WHOLE file as rule text — surface the warn channel in your host.
