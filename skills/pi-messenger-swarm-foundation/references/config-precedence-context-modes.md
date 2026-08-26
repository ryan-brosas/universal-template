<!-- capsule-v2 -->
# Config merge precedence & context-mode degradation — how do four config layers compose, and what do minimal/none modes actually drop?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Which fields win in a merge and which are forced off by contextMode?

## Spread-order precedence + tri-mode field forcing
**Path/Symbol:** `config.ts:loadConfig` (:128-221), `DEFAULT_CONFIG` (:34-50), `matchesAutoRegisterPath` (:68-95).
**Signature:** `loadConfig(cwd): MessengerConfig`.
**Data Shape:** layer order lowest→highest: `~/.pi/agent/settings.json → messenger` key, `~/.pi/agent/pi-messenger.json`, `<cwd>/.pi/pi-messenger.json`. Booleans default-true use `x !== false`; opt-ins default-false use `=== true`.

### Decisive source
```ts
const merged = { ...DEFAULT_CONFIG, ...settingsConfig,
                 ...(extensionConfig ?? {}), ...(projectConfig ?? {}) };
...
if (merged.contextMode === 'none') {
  return { ..., contextMode: 'none',
    registrationContext: false, replyHint: false, senderDetailsOnFirstContact: false, ... };
}
if (merged.contextMode === 'minimal') {
  return { ..., registrationContext: false, replyHint: true, senderDetailsOnFirstContact: false, ... };
}
```
Glob grammar (only TWO forms):
```ts
if (expanded.endsWith('/*')) { base prefix-or-equal match }
else if (expanded.endsWith('*')) { plain prefix match }
else { exact equality }
```

**Flow:** raw merge is a flat object spread (later layers win wholesale per key — no deep merge), then sharedFields normalize types defensively (`typeof x === 'number'` guards), then the mode switch FORCES the context trio regardless of user values. maxConcurrentSpawns must be a positive number or falls back to 3.
**Invariant:** contextMode is not advisory — 'minimal' silently disables registration context AND sender details while keeping reply hints; porters who treat it as a hint will leak context into minimal setups. Auto-register paths support exactly two glob shapes; anything else is an exact path.
**Probe:** direct tests `tests/swarm/per-request-project.test.ts::reads config from the project directory, not the server startup cwd` (:35) + `::caches config per cwd` (:68) + `::project B config is used when caller cwd is project B` (:248); `grep -c "contextMode === 'none'" config.ts` (=1); `grep -n "endsWith('/*')" config.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "loadConfig DEFAULT_CONFIG matchesAutoRegisterPath contextMode maxConcurrentSpawns", limit: 5 });
```

## Verdict
Adopt flat-spread three-layer merge with typed normalization and mode-forced field groups; adapt file locations; extend the glob grammar only by keeping exact-match as the residual branch.
