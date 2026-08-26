<!-- capsule-v2 -->
# Slash-command expansion — file-based commands, arg parsing, substitution

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter load file-based slash commands (pi prompt templates), parse their args, substitute `$1`/`$@`, and expand a leading `/command` before sending to pi?

## Slash-command expansion
**Path/Symbol:** `src/acp/slash-commands.ts` (whole, 197L) + `src/acp/session.ts:prompt` (424-426).
**Signature:** `loadSlashCommands(cwd): FileSlashCommand[]`; `toAvailableCommands(fileCommands): AvailableCommand[]`; `parseCommandArgs(argsString): string[]`; `substituteArgs(content, args): string`; `expandSlashCommand(text, fileCommands): string`.
**Data Shape:** `FileSlashCommand = { name, description, content, source }`. Commands load from `~/.pi/agent/prompts/**/*.md` (user) then `<cwd>/.pi/prompts/**/*.md` (project), recursing subdirectories into `(user:sub)`/`(project:sub)` sources. Frontmatter `description` (or first content line, truncated to 60 chars) becomes the description.

### Decisive source
```ts
export function expandSlashCommand(text: string, fileCommands: FileSlashCommand[]): string {
  if (!text.startsWith('/')) return text
  const spaceIndex = text.indexOf(' ')
  const commandName = spaceIndex === -1 ? text.slice(1) : text.slice(1, spaceIndex)
  const argsString = spaceIndex === -1 ? '' : text.slice(spaceIndex + 1)
  const cmd = fileCommands.find(c => c.name === commandName)
  if (!cmd) return text          // unknown -> leave as-is
  const args = parseCommandArgs(argsString)
  return substituteArgs(cmd.content, args)
}
```
```ts
// session.prompt: pi RPC mode disables slash expansion, so do it here
const expandedMessage = expandSlashCommand(message, this.fileCommands)
```
```ts
// parseCommandArgs: bash-style quotes
if (ch === '"' || ch === "'") inQuote = ch
else if (ch === ' ' || ch === '\t') { if (current) { args.push(current); current = '' } }
// substituteArgs: $@ then $1..$n
result = result.replace(/\$@/g, args.join(' '))
result = result.replace(/\$(\d+)/g, (_m, num) => args[Number(num)-1] ?? '')
```

**Flow:** `loadSlashCommands` reads user then project prompt dirs, parsing frontmatter + content. `toAvailableCommands` de-dupes by name (first wins) into ACP `AvailableCommand`s. When a prompt arrives, `session.prompt` calls `expandSlashCommand` first (since pi RPC mode won't expand it), substituting `$1`/`$@` with parsed args; unknown commands pass through unchanged. (The built-in headless commands like `/compact` are handled separately in `PiAcpAgent.prompt` before this.)

**Invariant:** Slash expansion happens adapter-side because pi RPC mode disables it; an unknown `/command` passes through untouched; `$@` expands to all args joined, `$N` to the Nth arg (empty if missing); user commands load before project commands (project overrides by first-wins de-dupe).

**Probe:** `test/unit/slash-commands.test.ts` ("parseCommandArgs: handles quotes", "substituteArgs: replaces $1.. and $@", "expandSlashCommand: expands known command", "toAvailableCommands: de-dupes by name") and `test/component/session-events.test.ts` ("PiAcpSession: expands /command before sending to pi").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "expandSlashCommand loadSlashCommands substituteArgs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the file-based command loading, frontmatter parsing, bash-quote arg parsing, `$1`/`$@` substitution, and adapter-side expansion. Adapt the prompt directory paths and the frontmatter key names to the host. Omit the built-in headless command handlers (compact/session/name/steering/follow-up/changelog/export/autocompact) unless the target needs them.
