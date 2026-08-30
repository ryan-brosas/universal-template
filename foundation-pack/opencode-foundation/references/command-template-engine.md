<!-- capsule-v2 -->
# Command $N template engine — how do slash-command templates expand arguments, shell snippets, and file parts?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** What is the exact expansion order for `$1..$N`, `$ARGUMENTS`, `!`cmd``, and @file references — and which edge cases silently change meaning?

## Positional placeholder expansion with last-N swallow
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`command`, lines 1356–1481; regexes :1592–1596).
**Signature:** `command({sessionID, messageID?, agent?, model?, arguments, command, variant?}): Effect<SessionV1.WithParts>`.
**Data Shape:** Regexes: `bashRegex = /!`([^`]+)`/g`, `argsRegex = /(?:\[Image\s+\d+\]|"[^"]*"|'[^']*'|[^\s"']+)/gi` (quoted strings and `[Image N]` are single tokens), `placeholderRegex = /\$(\d+)/g`, `quoteTrimRegex` strips one leading+trailing quote. Model resolution ladder: `cmd.model` → command-agent's model → `input.model` → session current model.

### Decisive source
```ts
// prompt.ts:1383-1395 — highest $N swallows ALL remaining args
const withArgs = templateCommand.replaceAll(placeholderRegex, (_, index) => {
  const position = Number(index)
  const argIndex = position - 1
  if (argIndex >= args.length) return ""          // missing positional ⇒ EMPTY string, never error
  if (position === last) return args.slice(argIndex).join(" ")   // $N(last) = rest-of-line
  return args[argIndex]
})
const usesArgumentsPlaceholder = templateCommand.includes("$ARGUMENTS")
let template = withArgs.replaceAll("$ARGUMENTS", input.arguments)
if (placeholders.length === 0 && !usesArgumentsPlaceholder && input.arguments.trim()) {
  template = template + "\n\n" + input.arguments   // no placeholders at all ⇒ append raw
}
```

**Flow:** lookup command (missing ⇒ typed error listing available names) → tokenize args → expand positionals with last-N-rest rule → expand `$ARGUMENTS` or append-raw fallback → run every `` !`cmd` `` snippet via configured preferred shell (`Process.text(..., {nothrow:true})`) and splice results by index → trim → resolvePromptParts for `@file` mentions, deduped against caller-supplied file parts by path → subtask decision: `(agent.mode === "subagent" && cmd.subtask !== false) || cmd.subtask === true` ⇒ single SubtaskPart carrying the first text part as prompt, executed under the CALLER's agent/model; else normal prompt under the command's agent/model → fire `plugin.trigger("command.execute.before")` → prompt() → publish `Command.Event.Executed`.
**Invariant:** Expansion order matters: positionals BEFORE `$ARGUMENTS` BEFORE shell interpolation BEFORE file resolution. The last placeholder is variadic — a porter who expands `$2` as a single arg breaks multi-word tails; one who errors on missing args breaks every zero-arg invocation of templates that reference `$1`.
**Probe:** `packages/opencode/test/session/prompt.test.ts:1786` "command ! expansion uses configured shell over env shell" (`shell:"bash"` config + `[[ 1 -eq 1 ]]` POSIX-failing snippet asserting "configured" reaches model input); `:2415` unknown command typed error with available names.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
```

## Verdict
Adopt token grammar, last-placeholder-variadic rule, empty-on-missing semantics, append-raw fallback, and shell-config preference; adapt Process/shell helpers; omit built-in command catalog.
