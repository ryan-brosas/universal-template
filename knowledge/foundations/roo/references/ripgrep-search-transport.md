<!-- capsule-v2 -->
# Ripgrep search transport — How do you bound, parse, and access-control an unbounded external grep process for LLM consumption?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory project `Roo-Code`. **Question:** When shelling out to `rg` for the agent's search tool, how must arguments, output limiting, and ignore-filtering be ordered so results stay bounded, parseable, and permission-safe?

## Connected graph-selected seam
**Path/Symbol:** `src/services/ripgrep/index.ts:regexSearchFiles` (:139-229); `execRipgrep` (:99-137); `getBinPath` (:85-97); `truncateLine` (:79-81).
**Signature:** `async function regexSearchFiles(cwd: string, directoryPath: string, regex: string, filePattern?: string, rooIgnoreController?: RooIgnoreController): Promise<string>`; internal `execRipgrep(bin: string, args: string[]): Promise<string>`; `truncateLine(line: string, maxLength = 500): string`.
**Data Shape:** Returns a formatted STRING (never structured data, never throws for search failures): header line (`Found N results.` or `Showing first 300 of 300+ results.`), then per file `# <relative/path>`, lines as `%3d | <text>`, blocks closed by `----`. Constants: `MAX_RESULTS=300`, `MAX_LINE_LENGTH=500`. Sole production caller: `src/core/tools/SearchFilesTool.ts:59` passing `task.rooIgnoreController`.

### Decisive source
```ts
const args = ["--json", "-e", regex]

// Only add --glob if a specific file pattern is provided
// Using --glob "*" overrides .gitignore behavior, so we omit it when no pattern is specified
if (filePattern) {
	args.push("--glob", filePattern)
}

args.push("--context", "1", "--no-messages", directoryPath)
// ...
let lineCount = 0
const maxLines = MAX_RESULTS * 5 // limiting ripgrep output with max lines since there's no other way to limit results...
rl.on("line", (line) => {
	if (lineCount < maxLines) {
		output += line + "\n"
		lineCount++
	} else {
		rl.close()
		rgProcess.kill()
	}
})
```

**Flow:** (1) `getBinPath` probes four VSCode-install layouts (`node_modules/@vscode/ripgrep/bin/`, `node_modules/vscode-ripgrep/bin`, both `node_modules.asar.unpacked` variants) → throw `"Could not find ripgrep binary"` if absent. (2) Spawn `rg --json -e <regex> [--glob <pattern>] --context 1 --no-messages <dir>`; read stdout through a readline interface (`crlfDelay: Infinity` for cross-platform CRLF). (3) Kill-ladder: after `MAX_RESULTS*5 = 1500` lines close the interface and SIGTERM the child — the author-recommended cross-platform substitute for `head`. (4) On close: non-empty accumulated stderr ⇒ reject ⇒ the caller catches and returns the literal string `"No results found"` (search errors degrade to an empty-looking answer, never an exception path). (5) Parse stdout as JSONL state machine: `begin` opens a file bucket, `match`/`context` append `{line_number, truncated text, isMatch, column}`, `end` closes it; consecutive lines (`line_number <= lastLine.line + 1`) merge into ONE result block. (6) POST-HOC access control: if a `rooIgnoreController` was passed, filter whole file buckets through `validateAccess(result.file)` AFTER parsing. (7) `formatResults`: cap at 300 file-buckets, relativize paths against `cwd`, pad line numbers to width 3, trim-end each line, `----` between blocks.

**Invariant:** Four properties a porter gets wrong: (a) OMIT `--glob` when no file pattern was requested — passing `--glob "*"` silently overrides `.gitignore`/`.ignore` semantics and floods the budget with vendored noise; (b) the ONLY output bound is the line-count kill-ladder (`rg` cannot be told to stop after N matches portably) — and because each match/context event is one JSONL line with ≤1 context line on each side plus begin/end, 5× is the safe ceiling multiplier; (c) ignore filtering runs AFTER assembly, so matches inside ignored paths CONSUME the 300-result budget before being dropped — a repo with many ignored hits starves visible ones (accepted trade: keeps the kill-ladder simple; a pre-filter would need `rg` globs derived from the ignore file); (d) `column` is populated with `absolute_offset` (byte offset), NOT the match column — downstream display treats it as opaque. Plus cosmetic contract: overlong lines get `substring(0,500) + " [truncated...]"` appended, and the final string is `.trim()`ed.

**Probe:** No direct spec exists for this module at pin (see Verdict caveat). Deterministic real-source probe executed this pass: `truncateLine` extracted VERBATIM from `src/services/ripgrep/index.ts:79-81` and exercised in node — 400-char line passes through unchanged; 600-char line returns exactly 500 chars + ` [truncated...]`. Consumer wiring pinned at `SearchFilesTool.ts:8,59`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "regexSearchFiles", limit: 5, fields: ["signature", "name", "file"] });
// → Roo-Code.src.services.ripgrep.regexSearchFiles Function src/services/ripgrep/index.ts 139-229
```

## Verdict
Adopt the argument shape (`--json -e` first, conditional `--glob`, trailing path), the 5× line-ceiling kill-ladder, JSONL begin/match/context/end merging, and post-hoc ACL filtering as one indivisible transport contract. Adapt binary discovery (`getBinPath`'s VSCode-layout probing) to your host's ripgrep location, and swap the `vscode.env.appRoot` dependency for an injected path. Omit the VSCode import surface. Coverage caveat stated honestly: NO `__tests__` spec covers `src/services/ripgrep/` at this HEAD — behavior is pinned by whole-file source reading + the executed `truncateLine` probe + the consumer call site; treat the merge/threshold constants as source-read truth, not test-pinned truth. A sibling twin exists at `src/services/glob/list-files.ts:649-727` (its own `execRipgrep`) serving the file-LISTING question — deliberately not mined under this capsule.
