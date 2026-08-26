<!-- capsule-v2 -->
# Permission rule grammar — escaped-parens Tool(content) with degrade-to-tool-name parsing

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you encode arbitrary strings (commands containing parentheses) into a flat `Tool(content)` permission-rule grammar without ambiguity, and what happens to malformed rules?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/permissionRuleParser.ts` — `escapeRuleContent` (:55-60), `unescapeRuleContent` (:74-79), `permissionRuleValueFromString` (:93-133), `findFirstUnescapedChar` (:158-175), `LEGACY_TOOL_NAME_ALIASES` (:21-29), `normalizeLegacyToolName` (:31-33).
**Signature:** `permissionRuleValueFromString(ruleString: string): PermissionRuleValue` where `PermissionRuleValue = { toolName: string; ruleContent?: string }`.
**Data Shape:** Grammar is `ToolName` or `ToolName(content)`; parens in content are backslash-escaped (`\(`, `\)`); a char is "unescaped" iff preceded by an EVEN number of backslashes.

### Decisive source
```ts
// Empty content (e.g., "Bash()") or standalone wildcard (e.g., "Bash(*)")
// should be treated as just the tool name (tool-wide rule)
if (rawContent === '' || rawContent === '*') {
  return { toolName: normalizeLegacyToolName(toolName) }
}
```

**Flow:** scan for FIRST unescaped `(` → LAST unescaped `)` → reject unless the closer is the FINAL character → missing toolName, empty content, or `*` all degrade to a bare tool-name (tool-wide) rule → else unescape content and return `{toolName, ruleContent}`. Escaping order matters and is asymmetric: escape backslashes FIRST then parens (:47-49); unescape parens FIRST then backslashes (:66-68) — reversing either round-trips wrongly. Legacy tool names (`Task`, `KillShell`, `AgentOutputTool`, `BashOutputTool`) are aliased to canonical names AT PARSE TIME (:21-33), so every downstream consumer sees canonical names only; deletion/dedup code normalizes raw settings entries via a parse→serialize roundtrip for the same reason (permissionsLoader.ts :184-189).

**Invariant:** (1) Malformed input NEVER throws — it degrades to the WIDER tool-name rule (a security-relevant choice: `"Bash(npm install"` parses as allow-all-Bash, so renderers can't be tricked into displaying a narrower grant than is enforced... treat degradation as policy, not accident). (2) Escape/unescape order asymmetry is load-bearing; a porter who symmetrizes it corrupts stored rules containing literal backslashes. (3) Parse-time legacy aliasing means persisted old names keep working after tool renames — replicate at the parse boundary, not per consumer.

**Probe:** coverage caveat — no upstream unit tests reachable in this fork (tests/ holds shell scripts only). Deterministic pins from repo root: `grep -nF "rawContent === '' || rawContent === '*'" src/utils/permissions/permissionRuleParser.ts` → :126; `grep -nF 'closeParenIndex !== ruleString.length - 1' src/utils/permissions/permissionRuleParser.ts` → :111; `grep -nF 'Task: AGENT_TOOL_NAME' src/utils/permissions/permissionRuleParser.ts` → :22; graph `search_graph --project locoagent --query permissionRuleValueFromString` resolves shellRuleMatching.parsePermissionRule :159-184 (BM25 cross-hit; this symbol is a plain export).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "escapeRuleContent unescapeRuleContent normalizeLegacyToolName", limit: 5 });
```

## Verdict
Adopt the even-backslash escape test, the ordered escape/unescape pair, parse-time aliasing, and degrade-to-tool-wide malformed handling. Adapt the alias table to your tool names. Omit the KAIROS/Brief conditional require (ant-build DCE plumbing).
