<!-- capsule-v2 -->
# Mention parsing pipeline — how do you turn @-mentions into model-ready context blocks without leaking ignored files?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you rewrite user text containing @file/@folder/@problems/@git-changes/@terminal/slash-commands into clean references plus separate content blocks — and what does each mention type contribute on error?

## Existence-check first, replace-with-reference, content as pseudo-tool-results
**Path/Symbol:** `src/core/mentions/index.ts` (`parseMentions` :99-253; `MentionContentBlock` :51-57 / `ParseMentionsResult` :66-77; `formatFileReadResult` truncation header :79-97; `getFileOrFolderContentWithMetadata` :265-330; wrapper `src/core/mentions/processUserContentMentions.ts` `processUserContentMentions` :36+).
**Signature:** `parseMentions(text, cwd, fileContextTracker?, rooIgnoreController?, showRooIgnoredFiles=false, includeDiagnosticMessages=true, maxDiagnosticMessages=50, skillsManager?, currentMode="code"): Promise<ParseMentionsResult>`.
**Data Shape:** Result = `{text (rewritten), contentBlocks: {type: file|folder|..., path?, content, metadata?: {totalLines, returnedLines, wasTruncated, linesShown}}[], slashCommandHelp?, mode?}`.

### Decisive source
```ts
// PASS 1: resolve existence ONCE for all commands (async, parallel), incl. skill fallback
const commandExistenceChecks = await Promise.all(uniqueCommandNames.map(async (name) => {
    const command = await getCommand(cwd, name)
    if (command) return {commandName: name, command, skillContent: null}
    return {commandName: name, command: undefined,
            skillContent: await resolveSkillContentForMode(skillsManager, name, currentMode)}
}))
// PASS 2: only EXISTING commands get rewritten; unknown ones stay literal text
if (validCommands.has(commandName) || validSkills.has(commandName))
    parsedText = parsedText.replace(match, `Command '${commandName}' (see below for command content)`)
// File mentions become blocks formatted like read_file results — the model is TOLD it already read them:
return `${header}\nIMPORTANT: File content truncated.\nStatus: Showing lines ${start}-${end} of ${total}...
To read more: Use the read_file tool with offset=${end + 1} and limit=${DEFAULT_LINE_LIMIT}`
```
File-block ladder: binary → "Binary file omitted" note; `.rooignore`-denied → "ignored by .rooignore" note (never the content); read errors → block whose content IS the error text. Env mentions (`problems`, `git-changes`, commit hash `/^[a-f0-9]{7,40}$/`, `terminal`) append `<workspace_diagnostics>`/`<git_working_state>`/`<git_commit hash="…">`/`<terminal_output>` XML sections to `parsedText`, each with its own in-tag error fallback. The wrapper (`processUserContentMentions`) applies this ONLY to text blocks containing `<user_message>` and to string tool_result content, then appends blocks AFTER the user's block; the FIRST command carrying a `mode` wins and is returned to switch modes.
**Flow:** collect unique commands → parallel existence check (command or mode-filtered skill) → rewrite valid ones → regex-replace mention grammar with quoted references → per-mention content fetch into ordered blocks/XML sections → assemble slash-command help → return mode.
**Invariant:** Ignored/binary/missing files produce VISIBLE explanatory stubs instead of silent omission or raw failures; user text never contains file contents inline (blocks are separate so ordering/labels stay stable); a nonexistent slash-command mention remains untouched prose rather than becoming an empty reference.
**Probe:** `src/shared/__tests__/context-mentions.spec.ts` (:3-150 regex grammar incl. boundary + log-paste negatives); `src/__tests__/command-mentions.spec.ts` (command resolution flow).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parseMentions mentionRegex contentBlocks slashCommandHelp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-pass existence checking, separate-blocks-not-inline-content, tool-result-shaped file blocks with next-offset hints, and visible denial/error stubs. Adapt the mention vocabulary. The `<user_message>` gating in the wrapper is load-bearing — applying mention parsing to ALL text would corrupt non-user blocks.
