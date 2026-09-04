<!-- capsule-v2 -->
# Sandbox settings schema & policy locks — passthrough for undocumented knobs, managed-only domain collapse, and Linux glob warnings

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How are sandbox settings typed so enterprise policy can lock them and undocumented knobs survive validation — and which platform gaps must be warned about instead of enforced?

## Schema, policy-lock, platform-gap plane
**Path/Symbol:** `src/entrypoints/sandboxTypes.ts` : `SandboxSettingsSchema` (:91-144), `SandboxNetworkConfigSchema` (:14-42), `SandboxFilesystemConfigSchema` (:47-86); consumers in `src/utils/sandbox/sandbox-adapter.ts` — `areSandboxSettingsLockedByPolicy` (:650-667), `shouldAllowManagedSandboxDomainsOnly` (:152-157) / `shouldAllowManagedReadPathsOnly` (:159-164), `getLinuxGlobPatternWarnings` (:600-645); `/sandbox` command gate `src/commands/sandbox-toggle/sandbox-toggle.tsx` :24-40.
**Signature:** zod v4 lazy schemas; `.passthrough()` keeps undocumented keys (enabledPlatforms) flowing; `addToExcludedCommands(command, permissionUpdates?)` extracts a Bash-rule prefix via local copies of the rule parser (:63-81) to dodge a circular import.
**Data Shape:** settings booleans + arrays as documented in-schema (`allowManagedDomainsOnly`, `allowManagedReadPathsOnly`, `failIfUnavailable`, `allowUnsandboxedCommands`, `enableWeakerNetworkIsolation` flagged '**Reduces security**' in its describe text).

### Decisive source
```ts
function areSandboxSettingsLockedByPolicy(): boolean {
  const overridingSources = ['flagSettings', 'policySettings'] as const
  for (const source of overridingSources) {
    const settings = getSettingsForSource(source)
    if (
      settings?.sandbox?.enabled !== undefined ||
      settings?.sandbox?.autoAllowBashIfSandboxed !== undefined ||
      settings?.sandbox?.allowUnsandboxedCommands !== undefined
    ) {
      return true
    }
  }
  return false
}
```

**Flow:** The lock detector answers "would a local change be ineffective?" by checking whether ANY higher-priority source DEFINES one of the three writable keys — presence, not value, is what locks. `/sandbox toggle` refuses to open when locked or when the platform is outside enabledPlatforms, and `setSandboxSettings` writes only to localSettings. Managed-only flags collapse config compilation to policy sources at two points: network domains (allowed side only — denied domains still honored from every source) and filesystem allowRead (policy-only when `allowManagedReadPathsOnly`). Linux/WSL gets warnings-not-enforcement for glob-carrying path rules because bubblewrap cannot express globs; the warning fires only when sandbox is actually enabled and strips a trailing `/**` before testing for remaining metachars.

**Invariant:** (1) Lock-by-presence means an admin who merely states `enabled: false` in policy still freezes the user's toggle — the semantic is "who owns this knob", not "what did they choose". (2) Undocumented-but-real settings must ride `.passthrough()` or enterprise rollouts break on upgrade. (3) Where your enforcement engine can't express a user-facing feature (globs on bwrap), downgrade LOUDLY to warnings at startup rather than silently ignoring rules.

**Probe:** anchored at the locoagent repo root — `grep -n "'flagSettings', 'policySettings'" src/utils/sandbox/sandbox-adapter.ts` → :653; `grep -n "passthrough()" src/entrypoints/sandboxTypes.ts` → :143; `grep -n 'bubblewrap doesn.t support globs' src/utils/sandbox/sandbox-adapter.ts | head -1` → :601; `grep -n 'areSandboxSettingsLockedByPolicy' src/commands/sandbox-toggle/sandbox-toggle.tsx` → :33; `grep -n "trimmedArgs.slice('exclude '.length)" src/commands/sandbox-toggle/sandbox-toggle.tsx` → :53.

## Get live surrounding code
**Retrieve:**
```ts
// BM25 misses the zod Variable by name; name_pattern resolves it line-exact (:14-42).
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SandboxNetworkConfigSchema SandboxFilesystemConfigSchema zod lazySchema", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "SandboxNetworkConfigSchema" });
```

## Verdict
Adopt lock-by-presence for admin-owned knobs, passthrough for staged-rollout settings, and warn-don't-ignore for unenforceable rule shapes. Adapt source-priority names (user/project/local/flag/policy) to your settings stack. Omit the ant-only dynamic disabled-commands channel already covered in the exclusion-ladder capsule.
