<!-- capsule-v2 -->
# Tool result → text translation — diff-first, content-block, bash-details, JSON last resort

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How do you flatten pi's heterogeneous tool-result shapes into one text payload for a client that only renders text (and which shape wins)?

## Result flattener
**Path/Symbol:** `src/acp/translate/pi-tools.ts` whole file (51L): `toolResultToText(result: unknown): string`.
**Signature:** single export; input is untyped on purpose — pi tool results vary by tool.
**Data Shape:** canonical result `{content:[{type:'text',text}], details:{...}}`; specializations: edit → `details.diff`, bash → `details.stdout/stderr/exitCode` (with top-level fallbacks `stdout/output/stderr/exitCode/code`).

### Decisive source
```ts
// 1) EDIT: terse message in content hides the useful payload — prefer the unified diff
const diff = details?.diff
if (typeof diff === 'string' && diff.trim()) return diff
// 2) generic: join text blocks
if (Array.isArray(content)) { const texts = ...; if (texts.length) return texts.join('') }
// 3) BASH: stdout lives in details, not content — ladder with ?? across details and top level
const stdout = details?.stdout ?? result?.stdout ?? details?.output ?? result?.output
const stderr = details?.stderr ?? result?.stderr
const exitCode = details?.exitCode ?? result?.exitCode ?? details?.code ?? result?.code
if (nonEmpty(stdout) || nonEmpty(stderr)) {
  const parts = [stdout?, stderr ? `stderr:\n${stderr}` : null, exitCode != null ? `exit code: ${n}` : null]
  return parts.join('\n\n').trimEnd()
}
// 4) last resort
try { return JSON.stringify(result, null, 2) } catch { return String(result) }
```

**Flow:** order IS semantics — a porter who checks `content` before `details.diff` ships the terse "edit applied" line instead of the diff the IDE wants to render. Same for bash: its content blocks are often empty while the real output sits in `details`. The exit-code suffix is appended ONLY when some output was found; a result with neither output nor blocks falls to pretty-printed JSON so nothing is ever silently dropped as empty string.

**Invariant:** the function never throws (JSON.stringify guarded); every branch returns a non-null string; `diff.trim()` guard means a whitespace-only diff does not shadow the content blocks beneath it. Type-check each field before use (`typeof === 'string'/'number'`) because shapes come from a subprocess.

**Probe:** `test/unit/pi-tools.test.ts` — "extracts text from content blocks" (:5), "prefers details.diff when present" (:15), "falls back to JSON" (:23), "extracts bash stdout/stderr from details" (:28).
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "toolResultToText details.diff stdout exitCode", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung precedence (diff → text blocks → bash details ladder → JSON). Adapt the bash key aliases to your agent's actual result schema. Omit nothing — 51 lines port whole.
