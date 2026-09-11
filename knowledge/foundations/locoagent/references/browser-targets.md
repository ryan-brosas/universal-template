<!-- capsule-v2 -->
# Browser target registry — how do independent scripts agree on which CDP port, profile dir, proxy, and device each platform uses?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When several tools (launcher, engine, doctor) must never disagree about a platform's browser coordinates, where does the truth live and how is an entry resolved?

## Registry-driven resolution with profile derivation
**Path/Symbol:** `scripts/lib/browser-targets.ts`:`parseRegistry`, `loadTargets`, `resolveTarget`, `resolveEntry`, `cdpUp`, `healthCheck` (`:45-143`).
**Signature:** `resolveTarget(platform: string, registryPath?, env?, host?): ResolvedTarget`; `cdpUp(port: number): Promise<boolean>`; `healthCheck(platform, ...): Promise<{ platform, port, profile, up }>`.
**Data Shape:** Registry JSON `{ version: 1, targets: Record<platform, TargetEntry> }` at `config/browser-targets.json`; `TargetEntry { cdpPort: number, profile?: string|null, useLegacyProfile?: boolean, proxy?: string|null, device?: DeviceTarget|null, account?: string }` resolves to `ResolvedTarget { platform, cdpPort, profile, proxy?, device }`.

### Decisive source
```ts
const explicit = entry.profile?.trim()
const base = defaultWorkProfile(host, env)
const profile = explicit
  ? explicit
  : entry.useLegacyProfile
    ? base                                   // no-suffix legacy path (pre-existing X login)
    : `${base}-${platform}`                  // per-platform cookie isolation
const device =
  entry.device && isDeviceTarget(entry.device) ? entry.device : resolveDevice(env)
...
export async function cdpUp(port: number): Promise<boolean> {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/json/version`)
    return res.ok
  } catch { return false }
}
```

**Flow:** parse+validate registry (throws on non-object / missing `targets`) → resolve every entry eagerly (throws on non-numeric cdpPort with the platform named) → unknown platform throws `Unknown platform "<p>". Known: ...` listing the alternatives. Health is a plain GET of the CDP `/json/version` endpoint — no SDK needed.
**Invariant:** The registry file is the SINGLE source of truth consumed by `setup-chrome.ts`, `workflow-engine.ts` (via `buildConfigJson`), and `doctor.ts`, so port/profile drift between launchers is structurally impossible. A null/absent profile derives `<base>-<platform>` for cookie isolation; only `useLegacyProfile: true` yields the shared no-suffix path (back-compat with an existing login).
**Probe:** `scripts/lib/browser-targets.test.ts` — `parseRegistry rejects a non-object / missing targets` (:23), `loadTargets derives a suffixed profile per platform` (:28), `useLegacyProfile derives the no-suffix profile` (:36), `resolveTarget throws a clear error for an unknown platform` (:57), `loadTargets rejects a non-numeric cdpPort` (:62).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "resolveTarget browser targets registry cdpPort", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the registry-as-single-source pattern, the explicit > legacy-no-suffix > suffixed-derivation profile precedence, and the `/json/version` health probe. Adapt the registry path and default port. Omit nothing in resolution — the suffix rule IS the cookie-isolation invariant.
