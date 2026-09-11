<!-- capsule-v2 -->
# Idempotent Chrome bring-up — how does setup converge to "CDP up + daemon attached" without ever duplicating browsers or wiping logins?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the safe order of operations for (re)starting an isolated CDP browser, and when is a profile wiped vs. preserved?

## Fast-path reconnect, reset-only wipe, resilient fan-out
**Path/Symbol:** `scripts/setup-chrome.ts`:`setupTarget`, `connectAgentBrowser`, `clearStaleDaemon` (`:81-206`).
**Signature:** `setupTarget(t: ResolvedTarget): Promise<{ fresh: boolean; ok: boolean }>`.
**Data Shape:** Per-target outcome `{ fresh, ok }` where `fresh = !existsSync(profile)` BEFORE launch; aggregated `failed: string[]` decides the process exit code.

### Decisive source
```ts
// Fast path: already up and not resetting → leave it running.
if (await cdpUp(t.cdpPort)) {
  if (!RESET) return { fresh: false, ok: true }
  await killChromeForProfile(t.profile, cfg.host); killed = true; await Bun.sleep(1000)
}
...
const fresh = !existsSync(t.profile)
if (fresh) {
  // Copy the user's real Chrome User Data dir so all platforms start with cookies.
  const sourceUserData = resolve(defaultSourceProfile(cfg.host), '..')
  if (existsSync(sourceUserData)) cpSync(sourceUserData, t.profile, { recursive: true })
  else mkdirSync(t.profile, { recursive: true })
}
launchChromeDetached(cfg.chromeBin, [
  `--remote-debugging-port=${t.cdpPort}`,
  `--user-data-dir=${t.profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-default-apps',
], cfg.host)
for (let i = 1; i <= 15; i++) {           // poll CDP readiness, 1s apart
  if (await cdpUp(t.cdpPort)) return { fresh, ok: true }
  await Bun.sleep(1000)
}
```

**Flow:** pin agent-browser's default port FIRST (`syncAgentBrowserConfig`) so the pin exists even if a later launch fails → per target: up-and-not-reset ⇒ leave as-is → `--reset` ⇒ kill scoped by profile, sleep, wipe `rmSync(profile)` → fresh ⇒ seed from real Chrome profile (or empty dir) → launch detached → poll `/json/version` up to 15 s, on timeout print the exact recovery command (`setup-chrome --target <p> --reset`) and report `ok:false` WITHOUT aborting sibling targets → connect the daemon only to the default target and only if it launched OK. Daemon connect MUST ignore stdout/stderr: `connect` forks a persistent daemon that would otherwise inherit the pipe and hang any caller reading to EOF.
**Invariant:** Wipes happen ONLY under explicit `--reset`, only after a profile-scoped kill plus settle sleep (never rm a live profile dir); non-reset bring-up is strictly convergent/idempotent — re-running can reconnect but never destroys session state. First-run detection is exactly `!existsSync(profile)` at launch time, which is what triggers the one-time manual login instruction.
**Probe:** No direct test file for `setup-chrome.ts` itself (coverage caveat — source-grounded). The unit-tested pieces it composes are pinned in `scripts/lib/host.test.ts`, `browser-targets.test.ts`, and `agent-browser-config.test.ts`; deterministic probe: `search_graph --name-pattern "^setupTarget$"` resolves `locoagent.scripts.setup-chrome.setupTarget`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "setupTarget CDP ready reset wipe profile", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt fast-path-if-up convergence, kill-then-wipe-only-on-reset, profile seeding from real Chrome, bounded CDP readiness polling with an actionable timeout message, and pipe-safe daemon connection. Adapt ports/paths/daemon CLI names. Omit the multi-target fan-out if you have one platform — keep the resilience rule (one failed target never blocks the others).
