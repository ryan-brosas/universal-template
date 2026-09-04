<!-- capsule-v2 -->
# available_commands_update ordering + merge ladder — when may you advertise commands, and whose name wins?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** After `session/new`, when is it safe to push the slash-command list to the client, how are agent-native, file-based, and adapter built-in commands merged, and what happens when the agent's command listing RPC fails?

## Advertisement ordering + mergeCommands
**Path/Symbol:** `src/acp/agent.ts` — advertisement blocks in `newSession` (:525-560) and `loadSession` (:1519-1553); `builtinAvailableCommands` (:94-134), `mergeCommands` (:136-148); fallback `src/acp/slash-commands.ts:toAvailableCommands` (:123-139); filter `src/acp/pi-commands.ts:toAvailableCommandsFromPiGetCommands` (:22-59).
**Signature:** `mergeCommands(a: AvailableCommand[], b: AvailableCommand[]): AvailableCommand[]`; `builtinAvailableCommands(): AvailableCommand[]`.
**Data Shape:** Merge order = `[pi get_commands (skill-gated, extensions excluded) + file-command inputs]` then `builtinAvailableCommands()` — 8 adapter-owned entries (`compact`, `autocompact`, `export`, `session`, `name`, `steering`, `follow-up`, `changelog`) with input hints.

### Decisive source
```ts
// Advertise slash commands (ACP: available_commands_update)
// Important: some clients (e.g. Zed) will ignore notifications for an unknown sessionId.
// So we must send this *after* the session/new response has been delivered.
setTimeout(() => {
  void (async () => {
    try {
      const pi = (await session.proc.getCommands()) as any
      const { commands } = toAvailableCommandsFromPiGetCommands(pi, {
        enableSkillCommands, includeExtensionCommands: false
      })
      await this.conn.sessionUpdate({ sessionId: session.sessionId,
        update: { sessionUpdate: 'available_commands_update',
          availableCommands: mergeCommands(withFileCommandInputs(commands, fileCommands),
                                           builtinAvailableCommands()) } })
      return
    } catch { /* Fall back to file-based prompt templates (legacy behavior). */ }
    await this.conn.sessionUpdate({ sessionId: session.sessionId,
      update: { sessionUpdate: 'available_commands_update',
        availableCommands: mergeCommands(toAvailableCommands(fileCommands),
                                         builtinAvailableCommands()) } })
  })()
}, 0)
```
```ts
function mergeCommands(a, b) {
  // Preserve order, de-dupe by name (first wins).
  const out = []; const seen = new Set<string>()
  for (const c of [...a, ...b]) { if (seen.has(c.name)) continue; seen.add(c.name); out.push(c) }
  return out
}
```

**Flow:** session/new returns → setTimeout(0) defers the advertisement one macrotask so the response reaches the client first → try agent's getCommands → filter (extension commands hidden, skill gate honored) → overlay file-command input hints → append builtins with first-wins dedupe; on ANY getCommands failure degrade to legacy file-template list + builtins. loadSession re-runs the identical block because a reload tears down the old subprocess.
**Invariant:** `available_commands_update` must never race the session/new response (unknown-sessionId clients silently drop it); merge is order-preserving with first-name-wins; the advertised list must stay consistent with what `prompt()` actually intercepts or executes (builtins here, expansion in session.prompt()).
**Probe:** `test/unit/merge-commands.test.ts` ("mergeCommands: preserves order and de-dupes (first wins)" — CAVEAT: this suite contains a local mirror impl "mirrors src/acp/agent.ts behavior", it does not import the symbol; algorithm pinned, symbol wiring pinned instead by the two consumer call sites). End-to-end: `node scripts/smoke-session.mjs` GREEN at dist 3d5ffcd2e2d8.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "pi-acp", function_name: "pi-acp.src.acp.agent.mergeCommands", direction: "inbound", depth: 2 });
// -> callers_total 2: PiAcpAgent.loadSession, PiAcpAgent.newSession
```

## Verdict
Adopt respond-then-defer advertisement ordering and the three-layer first-wins merge (agent native → file inputs → adapter builtins) plus the getCommands-failure legacy fallback. Adapt the builtin table to commands your host actually intercepts. Omit nothing else. Coverage caveat recorded for the mirror-style direct test.
