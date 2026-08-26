<!-- capsule-v2 -->
# Feature-gate ladder — in what order must CLI flag, env var, config default, session type, and feature flag resolve when deciding whether a capability turns on?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the canonical precedence when several opt-in/out mechanisms can disagree?

## chrome-feature-gate-ladder
**Path/Symbol:** `src/utils/claudeInChrome/setup.ts` (`shouldEnableClaudeInChrome` :39-68, `shouldAutoEnableClaudeInChrome` :70-84).
**Signature:** `shouldEnableClaudeInChrome(chromeFlag?: boolean): boolean`; `shouldAutoEnableClaudeInChrome(): boolean` (memoized via module-level `shouldAutoEnable`).
**Data Shape:** inputs: explicit boolean CLI flag; env `CLAUDE_CODE_ENABLE_CFC` (truthy/falsy via `isEnvTruthy`/`isEnvDefinedFalsy`); global-config key `claudeInChromeDefaultEnabled`; session kind from bootstrap state; StatSig-style feature value `tengu_chrome_auto_enable`.

### Decisive source
```ts
// Disable by default in non-interactive sessions (e.g., SDK, CI)
if (getIsNonInteractiveSession() && chromeFlag !== true) {
  return false
}

// Check CLI flags
if (chromeFlag === true) { return true }
if (chromeFlag === false) { return false }

// Check environment variables
if (isEnvTruthy(process.env.CLAUDE_CODE_ENABLE_CFC)) { return true }
if (isEnvDefinedFalsy(process.env.CLAUDE_CODE_ENABLE_CFC)) { return false }

// Check default config settings
const config = getGlobalConfig()
if (config.claudeInChromeDefaultEnabled !== undefined) {
  return config.claudeInChromeDefaultEnabled
}
return false
```

**Flow:** non-interactive veto FIRST (only an EXPLICIT `true` flag overrides it — `undefined` and even `false` cannot re-enable inside SDK/CI, but a deliberate human passed `--chrome`) → explicit CLI flag → env → persisted config default → hard `false`. Auto-enable is a separate AND-ladder: interactive AND cached-installed AND (ant OR flag), computed once per process.
**Invariant:** the non-interactive gate precedes everything except an explicit user gesture, because automation harnesses must never spawn browser bridges as a side effect; every tier short-circuits so lower tiers cannot resurrect the capability; tri-state config (`undefined` = unset vs `false` = user declined) is respected by checking `!== undefined` before trusting the value.
**Probe:** no upstream test. Deterministic pins: `grep -n "Disable by default in non-interactive" src/utils/claudeInChrome/setup.ts` → :40-41; `grep -n "claudeInChromeDefaultEnabled" src/utils/claudeInChrome/setup.ts` → :63.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "shouldEnableClaudeInChrome shouldAutoEnableClaudeInChrome", limit: 10 });
```

## Verdict
Adopt the five-tier precedence with the non-interactive veto and tri-state config check. Adapt mechanism names. Omit product-specific flags. Coverage caveat: no unit tests upstream.
