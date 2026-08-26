<!-- capsule-v2 -->
# channel allowlist per-entry dev flag — why does a session-wide "dev channels" bit not grant trust?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Two flags can enable development channels (`--dangerously-load-development-channels` and a dev dialog acceptance) — how does the allowlist avoid one flag silently trusting the other's entries?

## ChannelEntry / allowedChannels / hasDevChannels: per-entry dev bit + session-wide notice bit
**Path/Symbol:** `src/bootstrap/state.ts`:`ChannelEntry` `:37-39`, `allowedChannels` comment `:208-213`, `hasDevChannels` `:214-217`, accessors `getAllowedChannels`/`setAllowedChannels`/`getHasDevChannels`/`setHasDevChannels` (`:1676-1690`), initial values `:405-406`.
**Signature:** `type ChannelEntry = { kind: 'plugin'; name; marketplace; dev?: boolean } | { kind: 'server'; name; dev?: boolean }`; `setAllowedChannels(entries: ChannelEntry[]): void`; `getHasDevChannels(): boolean`.
**Data Shape:** Allowlist of tagged entries (discriminated union on `kind`). Trust decision reads the PER-ENTRY `dev` bit; `hasDevChannels` is display-only metadata naming the right policy flag in blocked messages.

### Decisive source
```ts
// :33-36 — the security rationale
// dev: true on entries that came via --dangerously-load-development-channels.
// The allowlist gate checks this per-entry (not the session-wide
// hasDevChannels bit) so passing both flags doesn't let the dev dialog's
// acceptance leak allowlist-bypass to the --channels entries.
// :208-213 — parsing happens once, tag decides trust model
// Parsed once in main.tsx — the tag decides trust model: 'plugin' →
// marketplace verification + allowlist, 'server' → allowlist always fails
// (schema is plugin-only). Either kind needs entry.dev to bypass allowlist.
```

**Flow:** CLI parse in main.tsx → each `--channels` entry becomes a ChannelEntry carrying its own `dev` provenance → session-wide `hasDevChannels` set if ANY entry was dev-sourced → at channel registration, gates check `entry.dev` for THAT entry only → ChannelsNotice reads `hasDevChannels` purely to phrase policy-block messages with the correct flag name.
**Invariant:** Authority must be scoped to the artifact it arrived with. A coarse session-wide boolean would create a privilege-leak composite: accepting dev channels via the dialog would also bless plain `--channels` entries (or vice versa). The session-wide bit exists ONLY for UX copy. Note the second invariant hiding in the comment: `'server'` kind is schema-impossible for plugins, so its allowlist check ALWAYS fails — fail-closed by construction rather than by validation error.
**Probe:** Deterministic pins: `grep -n 'leak allowlist-bypass' src/bootstrap/state.ts` → `36:`; `grep -n 'allowlist always fails' src/bootstrap/state.ts` → `212:`; `grep -n "dev?: boolean" src/bootstrap/state.ts | wc -l` → `2` (:38 + :39, one per union arm).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ChannelEntry allowedChannels hasDevChannels", limit: 10 });
```

## Verdict
Adopt per-entry provenance bits over session-wide grants wherever one flag can admit multiple item classes. Adapt entry kinds to your extension surface. Omit the notice-bit if your policy messages are generic.
