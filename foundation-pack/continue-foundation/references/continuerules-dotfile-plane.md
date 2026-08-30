<!-- capsule-v2 -->
# .continuerules dotfile plane — how does a single workspace dotfile become a rule?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What is the minimal contract for "one convention file per workspace" rules, and where does it sit in the rule precedence ladder?

## One plain file per workspace dir, fail-open, unshifted below markdown sources
**Path/Symbol:** `core/config/getWorkspaceContinueRuleDotFiles.ts:getWorkspaceContinueRuleDotFiles` (whole file, 32 lines); consumption `core/config/profile/doLoadConfig.ts:loadRules` (44–48).
**Signature:** `getWorkspaceContinueRuleDotFiles(ide: IDE): Promise<{ rules: RuleWithSource[]; errors: ConfigValidationError[] }>` with constant `SYSTEM_PROMPT_DOT_FILE = ".continuerules"`.
**Data Shape:** output rule = `{ rule: <raw file content string>, sourceFile: <dir>/​.continuerules, source: ".continuerules" }`; NO frontmatter parsing, no globs, no name — the whole file body is the rule text.

### Decisive source
```ts
for (const dir of dirs) {
  try {
    const dotFile = joinPathsToUri(dir, SYSTEM_PROMPT_DOT_FILE);
    if (await ide.fileExists(dotFile)) {
      const content = await ide.readFile(dotFile);
      rules.push({ rule: content, sourceFile: dotFile, source: ".continuerules" });
    }
  } catch (e) {
    errors.push({ fatal: false, message: `Failed to load system prompt dot file from workspace ${dir}: ...` });
  }
}
// loadRules consumes it FIRST of three unshifts:
const { rules: yamlRules } = await getWorkspaceContinueRuleDotFiles(ide);
rules.unshift(...yamlRules);   // => sits BELOW .continue/rules markdown, ABOVE yaml-plane rules
```

**Flow:** per workspace dir: join `.continuerules` → `ide.fileExists` gate → read → push raw-content rule; any throw becomes a NON-fatal error naming the dir (fail-open to empty). In final assembled order this plane lands between the markdown plane (`.continue/rules`, agent files, colocated cache) and the yaml assistant rules.
**Invariant:** existence is checked before read (a missing file is normal, not an error); errors are always non-fatal so one unreadable workspace never blocks config load; exactly one rule per workspace dir maximum (plain file, not a glob).
**Probe:** no dedicated suite at this pin (recorded caveat). Source-pinned observable: doLoadConfig.vitest.ts mocks the sibling loaders but exercises the real `loadRules` ordering contract; a workspace whose readFile throws yields `{ rules: [], errors: [non-fatal] }` by inspection of the try/catch scope.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "getWorkspaceContinueRuleDotFiles continuerules dotfiles", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.profile.doLoadConfig.loadRules", direction: "outbound", depth: 1 });
// observed callee edge: getWorkspaceContinueRuleDotFiles (first unshift in loadRules)
```

## Verdict
Adopt the "one well-known dotfile per root, raw text, checked-exists-then-read, non-fatal failure" pattern for user-convention prompt files; adapt the filename constant and where the plane sits in your precedence array; omit frontmatter support here entirely — richer grammar belongs to the markdown plane (see markdown-frontmatter-grammar.md).
