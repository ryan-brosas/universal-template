<!-- capsule-v2 -->
# CLI shortcuts readline loop — why is the shortcut registry rebuilt through a user callback that may throw?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the TTY gate, normalization contract, and the quit path's close-then-exit ordering.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/cliShortcuts.ts` — `isCliShortcutsEnabled` 7–8 (config.dev.cliShortcuts && isTTY('stdin')), `normalizeShortcutInput` 12, `setupCliShortcuts` 14–116 (custom validation 69–79, help 81–87, line handler 94–111, teardown return 113–115).
**Signature:** `setupCliShortcuts({help?, openPage, closeServer, printUrls, restartServer?, customShortcuts?, logger}): Promise<() => void>`.
**Data Shape:** CliShortcut {key, description, action}; 'r' entry exists ONLY when restartServer provided.

### Decisive source
```ts
{
  key: 'q',
  action: async () => { try { await closeServer(); } finally { process.exit(0); } },   // even failed close exits
}
```
```ts
shortcuts = customShortcuts(shortcuts);
if (!Array.isArray(shortcuts)) throw new Error('dev.cliShortcuts option must return an array of shortcuts.');
...
rl.on('line', (input) => {
  input = input.trim().toLowerCase();          // case-insensitive + whitespace tolerant
  if (input === 'h') { /* print registry */ }
  for (const s of shortcuts) if (input === s.key) { s.action(); return; }
});
```

**Flow:** enabled only when config AND stdin is a TTY — CI/piped stdin never installs the interface (and gracefulShutdown's stdin-end listener owns EOF instead). The 'h' help key is handled OUTSIDE the registry so user shortcuts can't shadow it accidentally... they CAN redefine it — the fixed handler runs first. Teardown closes the readline interface so the process can drain.
**Invariant:** (1) q MUST exit in finally — a hanging closeServer promise must not leave an unkillable process; (2) customShortcuts returning non-array throws BEFORE any listener attaches; (3) normalizeShortcutInput is exported + unit-pinned because plugins compose it for their own prompts.
**Probe:** unit `packages/core/tests/cliShortcuts.test.ts:4–7` (normalize table: ' H ', '\\to\\t', '  Q').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "setupCliShortcuts isCliShortcutsEnabled normalizeShortcutInput", limit: 8 });
```

## Verdict
Adopt TTY-gated install, normalized single-key dispatch with immutable help key, validated custom registries, and finally-exit quit. Adapt key set to host commands. Omit color styling.
