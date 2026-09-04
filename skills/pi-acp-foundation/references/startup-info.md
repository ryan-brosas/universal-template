<!-- capsule-v2 -->
# Startup info — synthesized prelude (pi version, skills, prompts, extensions, IDE bridge) + update notice

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter synthesize the "startup info" block (pi version, context, skills, prompts, extensions, IDE bridge status) and the "New version available" update notice, and how does `quietStartup` suppress it?

## Startup info
**Path/Symbol:** `src/acp/agent.ts` — `buildStartupInfo` (1688-1887), `buildBridgeStartupInfo` (1648-1686), `buildUpdateNotice` (1572-1599), `compareSemver`/`isSemver` (1549-1570), `readNearestPackageJson` (1889-1909).
**Signature:** `buildStartupInfo(opts): string`; `buildBridgeStartupInfo(opts): string`; `buildUpdateNotice(): string | null`.
**Data Shape:** The prelude is a Markdown string with `## Context`, `## IDE Bridge`, `## IDE Tools`, `## Skills`, `## Prompts`, `## Extensions` sections, a `pi v<ver>` header, and an optional update-notice footer. `quietStartup` (from settings) suppresses the full prelude but still surfaces the update notice.

### Decisive source
```ts
// buildUpdateNotice: fast best-effort npm check
const installed = (spawnSync('pi',['--version']).stdout || stderr).replace(/^v/i,'')
if (!installed || !isSemver(installed)) return null
const latest = (spawnSync('npm',['view','@earendil-works/pi-coding-agent','version'],{ timeout: 800 }).stdout || '').trim()
if (!latest || !isSemver(latest)) return null
if (compareSemver(latest, installed) <= 0) return null
return `New version available: v${latest} (installed v${installed}). Run: \`npm i -g @earendil-works/pi-coding-agent\``
```
```ts
// newSession: quietStartup suppresses the prelude but keeps the update notice
const preludeText = quietStartup
  ? updateNotice ? updateNotice + '\n' : ''
  : buildStartupInfo({ cwd, fileCommands, updateNotice, bridgeStatus, bridgeTools, ... })
if (preludeText) session.setStartupInfo(preludeText)
// ... after session/new returns, try to send it immediately (clients may ignore it -> first chunk of first prompt)
if (preludeText) setTimeout(() => session.sendStartupInfoIfPending(), 0)
```
```ts
// skill discovery: global (~/.pi/agent/skills + ~/.agents/skills) + project (.pi/skills), recursive SKILL.md + root .md
// prompts: ~/.pi/agent/prompts/*.md -> /name
// extensions: ~/.pi/agent/extensions/*.{ts,js} + npm: packages from settings
```

**Flow:** On `session/new`, the adapter builds the startup-info prelude (pi version via `pi --version`, context AGENTS.md, IDE bridge status/tools, skills/prompts/extensions discovery). `quietStartup` (global+project settings merge) suppresses the full prelude but keeps the update notice. The prelude is set on the session and emitted either immediately after `session/new` returns or as the first chunk of the first prompt (`sendStartupInfoIfPending`). `buildUpdateNotice` does a fast (800ms-timeout) npm registry check and compares semver.

**Invariant:** The update check must stay fast (800ms timeout) so it never slows `session/new`; `quietStartup` suppresses the verbose prelude but never hides a high-signal version notice; startup info is emitted at most once per session (the `startupInfoSent` flag).

**Probe:** `test/unit/startup-info-ide.test.ts` (IDE bridge guidance), `test/unit/startup-info-env.test.ts`, `test/unit/startup-info-project-packages.test.ts` (project packages from `.pi/settings.json`), and `test/unit/startup-info-load-session.test.ts` ("PiAcpAgent: does not emit startup info on loadSession").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "buildStartupInfo buildUpdateNotice quietStartup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synthesized startup-info prelude, the `quietStartup` suppression, the fast update-notice semver check, and the emit-once semantics. Adapt the pi version command, the skill/prompt/extension discovery paths, and the npm package name to the host. Omit the IntelliJ-specific IDE-tools guidance and the `readNearestPackageJson` walk unless the target needs them.
