<!-- capsule-v2 -->
# discord-command-registration-race

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-discord/src/adapter.ts` + `commands.ts`
- Symbol: `DiscordAdapter.registerCommands / publishCommands`
- Lines: registerCommands :172-178, publishCommands :185-197, start()'s ready handler :200-204
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-discord.src.adapter.DiscordAdapter.registerCommands`

## Question
The engine calls `registerCommands` AFTER `start()` resolves, but `start()` resolves before the gateway READY event — how do slash commands get published exactly once without ever being wiped?

## Signature & Data Shape
```typescript
registerCommands(commands: readonly CommandSpec[]): void;  // stash; publish now if already ready
private publishCommands(): Promise<void>;                  // empty-list guard; guild-scoped or global
```

## Decisive Source Excerpt
```typescript
registerCommands(commands: readonly CommandSpec[]): void {
  this.pendingCommands = commands;
  // `ready` may have already fired (start() resolves before the gateway READY
  // event, and the engine calls registerCommands AFTER start()). If so, the
  // once("ready") publish already ran with an empty list — publish now.
  if (this.isReady) void this.publishCommands();
}
private async publishCommands(): Promise<void> {
  if (this.pendingCommands.length === 0) return;  // an empty PUT CLEARS all of the bot's commands
  ...
}
```

## Flow
1. `start()` awaits `client.login()` — which resolves BEFORE gateway READY — so any code that runs right after `start()` is in a pre-READY window.
2. Commands are STASHED (`pendingCommands`) and published from two possible sites: the `once("ready")` handler (normal path) or a post-ready `registerCommands` call (late-engine path); whichever fires with actual commands wins, and re-publication is idempotent (a full PUT of the same list).
3. The empty-list guard makes "publish nothing yet" a no-op instead of a destructive clear — the race where READY beats the engine's registration cannot wipe production commands.
4. Guild-scoped registration (`opts.guildId`) gives instant availability in dev; global registration propagates slowly but fleet-wide.

## Invariant
Command publication must be idempotent and must NEVER issue an empty overwrite; stashed-state + dual publish sites make READY-vs-register ordering irrelevant.

## Direct-Test Probe
- File: `packages/channels-discord/src/adapter.test.ts`
- Line: :403 "registerCommands never clears on empty, and publishes when already ready"

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"DiscordAdapter registerCommands publishCommands pendingCommands","limit":10}'
```

## Verdict
Adopt stash + guarded dual-site publication for any platform where connection-readiness and API-registration have independent timing. Adapt to per-platform command APIs (Slack manifest vs Discord bulk PUT). Omit nothing — the empty-PUT guard is the whole defect class being prevented.
