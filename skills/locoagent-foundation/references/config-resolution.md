<!-- capsule-v2 -->
# Config resolution with blank-env semantics — how does one pure function keep the launcher and doctor from disagreeing about host, device, and paths?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Why must a blank `.env` placeholder be treated as "unset", and how is every host-specific default resolved in one testable place?

## Pure env → LocoConfig resolver with blank-means-default
**Path/Symbol:** `scripts/lib/config.ts`:`loadConfig`, `pick` (`:28-42`); consumers `setup-chrome.ts:37`, `doctor.ts`.
**Signature:** `loadConfig(env?: NodeJS.ProcessEnv, host?: HostOS): LocoConfig`; `pick(v?: string): string | undefined`.
**Data Shape:** `LocoConfig { host: HostOS, device: 'desktop'|'ios'|'android', chromeBin: string, workProfile: string, debugPort: number }`. Defaults: port 9222; work profile from `defaultWorkProfile(host)` unless `CHROME_WORK_PROFILE`; binary via `CHROME_BIN` else host candidates (throws if none).

### Decisive source
```ts
// Read an env var, treating blank/whitespace-only as absent. Env values can
// arrive empty from a blank `.env` placeholder or an exported-but-empty shell
// var; in both cases the intent is "use the default", not the empty string.
function pick(value: string | undefined): string | undefined {
  const trimmed = value?.trim()
  return trimmed ? trimmed : undefined
}
export function loadConfig(env = process.env, host = detectHost()): LocoConfig {
  const device = resolveDevice(env)
  const workProfile = pick(env.CHROME_WORK_PROFILE) ?? defaultWorkProfile(host, env)
  const debugPort = parseInt(pick(env.CHROME_DEBUG_PORT) ?? '9222', 10)
  const chromeBin = resolveChromeBinary(pick(env.CHROME_BIN), host)
  return { host, device, chromeBin, workProfile, debugPort }
}
```

**Flow:** resolve device (`DEVICE_PROFILE`, blank ⇒ desktop, invalid ⇒ throw listing valid values) → resolve work profile (explicit override or stable per-user dir) → parse port with blank ⇒ 9222 → resolve Chrome binary (throw with actionable "Set CHROME_BIN" message when absent) → return the frozen set both entry points consume. Everything is injected (env, host) so the function is pure and unit-testable without a real machine.
**Invariant:** Blank ≠ empty-string-as-value — a whitespace `CHROME_WORK_PROFILE=` previously crashed setup-chrome with `mkdirSync('')` ENOENT; after `pick`, it means default. Invalid values throw loudly instead of guessing. One resolver shared by launcher AND doctor makes config drift between them structurally impossible.
**Probe:** `scripts/lib/config.test.ts` — `loadConfig applies defaults (desktop, 9222)` (:27), `treats a blank CHROME_WORK_PROFILE as unset` (:37, cites the mkdirSync('') crash in its comment), `treats a whitespace-only CHROME_WORK_PROFILE as unset` (:44), `treats a blank CHROME_DEBUG_PORT as the 9222 default` (:50). Companion: `scripts/lib/device.test.ts` (`treats a blank DEVICE_PROFILE as desktop` :24).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "loadConfig pick blank env workProfile", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the single pure resolver, blank/whitespace-means-unset normalization for EVERY string env var, loud throws on invalid enum values, and dependency injection of env/host for testability. Adapt variable names and defaults. Omit nothing from `pick` — trimming whitespace-only values is the exact bug this repo hit in production.
