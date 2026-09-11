<!-- capsule-v2 -->
# Sandbox enablement gate + silent-failure surface — when the user's security setting is being ignored, who finds out?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you decide "is sandboxing on" across platform support, dependencies, and policy platform lists — and how do you avoid silently ignoring an explicitly-enabled security control?

## Enablement gate & failure surfacing
**Path/Symbol:** `src/utils/sandbox/sandbox-adapter.ts` : `isSandboxingEnabled` (:535-550), `getSandboxUnavailableReason` (:565-595), `isPlatformInEnabledList` (:508-529), memoized `checkDependencies` (:454-460) / `isSupportedPlatform` (:494-496); startup consumers `src/cli/print.ts` :601-625 + `src/screens/REPL.tsx` :2318.
**Signature:** `isSandboxingEnabled(): boolean`; `getSandboxUnavailableReason(): string | undefined`; `isSandboxRequired(): boolean = enabled && failIfUnavailable`.
**Data Shape:** settings booleans `sandbox.enabled`, `sandbox.failIfUnavailable`, undocumented `sandbox.enabledPlatforms: Platform[]` (read via zod `.passthrough()`); dependency check returns `{ errors: string[], warnings: string[] }`.

### Decisive source
```ts
function isSandboxingEnabled(): boolean {
  if (!isSupportedPlatform()) return false
  if (checkDependencies().errors.length > 0) return false
  if (!isPlatformInEnabledList()) return false
  return getSandboxEnabledSetting()
}
```

**Flow:** The gate is a pure AND of four predicates (platform supported → deps present → platform in enterprise `enabledPlatforms` → user enabled). The SECOND function exists because that AND is silent by construction: #34044 fixed the footgun where a user sets `sandbox.enabled: true` expecting domain enforcement, deps are missing, and every command runs unsandboxed with zero feedback. So at startup (print mode AND REPL), `getSandboxUnavailableReason()` produces a human-readable reason ONLY when the user explicitly asked for sandbox (no noise otherwise): WSL1-specific message, unsupported platform, not-in-`enabledPlatforms`, or missing-deps with platform-tuned hints (`/sandbox or /doctor` on macOS, `apt install bubblewrap socat` elsewhere). Then `isSandboxRequired()` (`failIfUnavailable`) decides warn-vs-refuse-to-start: print.ts exits via `gracefulShutdownSync(1)` with "refusing to start without a working sandbox".

**Invariant:** (1) An explicit-but-unenforceable security setting must be surfaced loudly or refused — silently downgrading it is worse than not having it, because users believe they are protected. (2) Memoized predicates (`memoize` from lodash-es) auto-invalidate because they key on the settings object identity — new settings object ⇒ cache miss; a porter caching on a primitive loses hot-reload. (3) `enabledPlatforms: []` (empty array) means DISABLED everywhere — distinct from `undefined` meaning no restriction; the NVIDIA-rollout comment documents this as an enterprise staged-rollout valve.

**Probe:** anchored at the locoagent repo root — `grep -n 'checkDependencies().errors.length > 0' src/utils/sandbox/sandbox-adapter.ts` → :540; `grep -n 'enabledPlatforms.length === 0' src/utils/sandbox/sandbox-adapter.ts` → :519; `grep -n 'const checkDependencies = memoize' src/utils/sandbox/sandbox-adapter.ts` → :454; `grep -n 'getSandboxUnavailableReason\|isSandboxRequired' src/cli/print.ts | head -2` → :601,:603; `grep -n 'refusing to start without a working sandbox' src/cli/print.ts` → :606; `grep -n 'enabledPlatforms is an undocumented setting' src/entrypoints/sandboxTypes.ts` → :104.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isSandboxingEnabled enabledPlatforms checkDependencies", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getSandboxUnavailableReason failIfUnavailable", limit: 5 });
```

## Verdict
Adopt the AND-gate plus the separate reason-surfacing pass (gate answers "on/off", reason answers "why off" — conflating them makes the gate noisy). Adapt the platform vocabulary (`macos|linux|wsl|windows`) and dep-check command to your runtime. Omit the ant-only WSL1 message special-case unless you ship WSL. Coverage caveat: no upstream unit tests; probes pin source anchors line-exact.
