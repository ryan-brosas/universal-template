<!-- capsule-v2 -->
# Secret env resolution — how do requested secret names become PTY env vars without ever touching the HTTP surface?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I resolve an automation's requested secrets to env vars at launch time, skipping every failure mode without clobbering pre-existing environment?

## Parallel resolve with two-sided skip
**Path/Symbol:** `packages/server/src/utils/build-automation-secret-env.ts:buildAutomationSecretEnv` (17–39); late attachment via run tracker `setEnv`/`setRedactionValues` (see pending-run-handoff).
**Signature:** `buildAutomationSecretEnv(requestedSecrets: readonly string[], secretStore: SecretStore, secretBackend: SecretBackend): Promise<Record<string, string>>`.
**Data Shape:** store maps name → policy `{envVar}`; backend maps name → value (`null` = absent). Returns `{}` when nothing requested OR backend unsupported — automations that name no secrets pay ZERO backend cost.

### Decisive source
```ts
// :26-33 — both misses skip; nothing overwrites a pre-existing var
const resolved = await Promise.all(
  requestedSecrets.map(async (name): Promise<ResolvedSecretVar | null> => {
    const entry = secretStore.get(name);
    if (!entry) return null;          // deleted since authored
    const value = await secretBackend.get(name);
    if (value === null) return null;  // locked Keychain / never set
    return { envVar: entry.envVar, value };
  }),
);
```

**Flow:** automation declares requested secret NAMES at authoring time; the daemon resolves them per-launch: policy lookup in the store, value lookup in the OS backend (macOS Keychain via native helper), parallel via `Promise.all`. Any miss (name deleted since authoring, value unavailable) yields null and is skipped — the remaining names still resolve. Values flow Keychain → daemon memory → PTY env only. The redaction twin: when the automation opts into `redactOutput`, the SAME resolved values are attached as redaction values so captured run logs have them scrubbed.
**Invariant:** an unset secret must never clobber (or be seen to overwrite) a pre-existing env var — absence SKIPS rather than writing empty; resolution errors are logged by callers and do NOT block the launch (the run starts without the failed secret). Env-var NAMES come from the validated policy store, never from raw user input at launch time.
**Probe:** `packages/server/tests/utils/build-automation-secret-env.test.ts` — `"returns an empty env when nothing is requested (zero backend cost)"` (:63 spy-pins no backend calls), `"skips a name deleted since the automation was authored (fail-closed)"` (:90), `"skips a secret with no value (locked Keychain / never set) without clobbering"` (:100), `"resolves in parallel"` (:111).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "parseOscAutomationExitFromChunk buildAutomationSecretEnv", limit: 6, detail: "compact" });
// → buildAutomationSecretEnv @ build-automation-secret-env.ts:17-39
```

## Verdict
Adopt the two-sided-skip parallel resolver verbatim for any "declare secrets once, inject per run" feature; adapt the backend interface to your OS credential store (inject it — don't port the Keychain helper); omit the redaction-values twin if output capture doesn't exist. 6 direct tests pin every branch at this commit.
