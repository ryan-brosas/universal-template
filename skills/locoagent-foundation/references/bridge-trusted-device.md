<!-- capsule-v2 -->
# Trusted-device enrollment — 10-minute window, staged flags, and memo-cache invalidation

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you add a device-bound credential layer to an API client when enrollment is only possible right after login?

## Path/Symbol
**Path/Symbol:** `src/bridge/trustedDevice.ts` — whole file: gate const (:33), env-precedence memoized read (:45-52), `getTrustedDeviceToken` (:54-59, gate checked LIVE per call), `clearTrustedDeviceToken` (:72-87, pre-enrollment wipe), `enrollTrustedDevice` (:98-210).
**Signature:** `getTrustedDeviceToken(): string | undefined` (undefined ⇒ header omitted, server no-ops); `enrollTrustedDevice(): Promise<void>` best-effort never-throws.
**Data Shape:** token persisted in OS keychain store as `trustedDeviceToken` (90d rolling); env override `CLAUDE_TRUSTED_DEVICE_TOKEN` wins over storage.

### Decisive source
```ts
// Enrollment (POST /auth/trusted_devices) is gated server-side by
// account_session.created_at < 10min, so it must happen during /login.
// Token is persistent (90d rolling expiry) and stored in keychain.
...
// Always re-enroll on /login — the existing token may belong to a
// different account (account-switch without /logout). Skipping enrollment
// would send the old account's token on the new account's bridge calls.
...
// Called before enrollTrustedDevice() during /login so a stale token from
// the previous account isn't sent as X-Trusted-Device-Token while
// enrollment is in-flight
```

**Flow:** two-flag rollout: CLI flag `tengu_sessions_elevated_auth_enforcement` controls whether the header flows at all; server flips its own later — headers start flowing (server no-ops) THEN enforcement turns on. Read path memoizes ONLY the keychain read (~40ms macOS `security` subprocess; bridgeApi calls it from getHeaders() on every poll/heartbeat) while the GATE is read live so a flag flip lands without restart. Enrollment: blocking gate check awaits any in-flight GrowthBook re-init → skip if env-var set (it would shadow the enrolled token anyway) → lazy-require auth.ts (~1300-module tree) → always re-enroll on login → persist + clear memo cache. Cache also cleared on logout (`clearAuthRelatedCaches`).

**Invariant:** (1) The clear-before-enroll ordering closes the account-switch race: without it, bridge calls between login and enrollment completion send the PREVIOUS account's token. (2) Memoize the expensive read, never the gate — gating semantics must be live. (3) Enrollment failure is universally non-fatal: post-login hooks must not block on it; every failure branch logs and returns. (4) Header absence must be a valid protocol state (server falls through to its flag-off path) so clients and servers can roll independently.

**Probe:** coverage caveat — no upstream unit tests for this file (vault-mode analog exercised via integration elsewhere). Deterministic pins: `grep -n "created_at < 10min" src/bridge/trustedDevice.ts` (:26 and :95); `grep -n "env var takes precedence" src/bridge/trustedDevice.ts` (:110-111); `grep -n "~40ms" src/bridge/trustedDevice.ts` (:39); graph resolves `locoagent.src.bridge.trustedDevice.enrollTrustedDevice` :98-210 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "enrollTrustedDevice getTrustedDeviceToken clearTrustedDeviceTokenCache trustedDeviceToken", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the staged two-flag rollout + window-bound enrollment + live-gate/memoized-read split for any device-binding credential scheme. Adapt endpoint/window to your server; omit nothing — the ordering traps here are security-relevant.
