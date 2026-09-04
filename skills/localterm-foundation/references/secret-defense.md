<!-- capsule-v2 -->
# Secret defense — how do secrets injected into the agent's own env stay out of its bash tool?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** When a harness injects secrets into its own process env, how do you stop agent-spawned commands from reading them (env) or printing them into context (output)?

## Two-layer defense over one threat model
**Path/Symbol:** `packages/pi-extension/extensions/bash-secret-scrub.ts:registerBashSecretScrub` (69–94), `wrapWithRedaction` (44–67); `src/utils/scrub-env.ts:scrubEnv` (6–13); `src/utils/redact-output.ts:redactText/overlapTailLen/createStreamingRedactor` (10–20 / 33–46 / 60–82); `src/constants.ts:REDACTION_MIN_VALUE_LENGTH=4, REDACTION_MASK="*"` (32/37).
**Signature:** `scrubEnv(env: NodeJS.ProcessEnv, strip: ReadonlySet<string>): NodeJS.ProcessEnv`; `createStreamingRedactor(values): { push(chunk): string; finish(): string }`; `wrapWithRedaction(operations: BashOperations, getValues: () => readonly string[]): BashOperations`.
**Data Shape:** layer 1 mutates nothing — returns `{ ...env }` minus stripped names; layer 2 wraps `operations.exec` so every `onData` chunk passes through a per-exec redactor before the tool accumulates it.

### Decisive source
```ts
// Layer 1 — pure spawn-side scrub (bash-secret-scrub.ts:80)
const spawnHook: BashSpawnHook = ({ command, cwd: spawnCwd, env }) => ({
  command, cwd: spawnCwd, env: scrubEnv(env, stripSet),
});
// Layer 2 — stream redaction with overlap-tail hold-back (redact-output.ts:67-73)
push(chunk) {
  pending += chunk;
  const safeLen = pending.length - overlapTailLen(pending, applicable);
  if (safeLen <= 0) return "";
  const safe = pending.slice(0, safeLen);      // safe slice ONLY — never emit the tail
  pending = pending.slice(safeLen);
  return redactText(safe, applicable);
}
```

**Flow:** values recomputed on `session_start` (`pi.on`, lines 75–78) → per exec, `getValues()` read lazily so a recompute applies without rebuilding the tool → empty values ⇒ zero-alloc pass-through (`push = chunk => chunk`) → otherwise chunks decode via `TextDecoder("utf-8", {stream:true})`, redact, emit; decoder-flush + `finish()` close the exec.
**Invariant:** `overlapTailLen` caps at `value.length` (NOT −1) because masking is length-changing and only the safe slice is ever emitted — a whole value sitting at the boundary must be held entirely so its head never leaks. Longer values scan first in `redactText` so a short substring cannot mask a longer match; values < 4 chars never redact (they substring-match ordinary output).
**Probe:** `packages/pi-extension/tests/redact-output.test.ts` — :53 "redacts a value split across two pushes without leaking its head" (first push must not contain the value's head), :69 "flushes an unmatched held tail verbatim on finish", :19 longer-first ordering, :47 zero-alloc pass-through. Scrub purity: `tests/scrub-env.test.ts` :23 distinct-object/no-mutation.

## Policy chain: names-only files, values from process.env
**Path/Symbol:** `packages/pi-extension/src/utils/read-localterm-secret-policy.ts:readLocaltermSecretEnvVarsForPi` (64–87); `read-secret-values.ts:readLocaltermSecretValuesForPi` (17–29); `constants.ts:SECRET_NAME_PATTERN/PROCESS_NAME_PATTERN/ENV_VAR_PATTERN` (22–24).
**Signature:** `readLocaltermSecretEnvVarsForPi(stateDirectory?): string[]`; `readLocaltermSecretValuesForPi(stateDirectory?, env = process.env): string[]`.
**Data Shape:** `~/.localterm/secrets.json` `{secrets:[{name,envVar}]}` + `processes.json` `{processes:[{name,requestedSecrets}]}` hold NAMES ONLY; find the `pi` process entry → map requestedSecrets→envVars → pull VALUES from process.env, dedupe, drop sub-floor values.

### Decisive source
```ts
// every entry must pass canonical patterns before it can strip anything:
.filter((entry) => SECRET_NAME_PATTERN.test(entry.name) && ENV_VAR_PATTERN.test(entry.envVar));
// ENV_VAR_PATTERN = /^[A-Z_][A-Z0-9_]*$/ — a hostile policy file can never
// trick the scrub into deleting an unrelated env var.
if (!piProcess) return [];            // missing/malformed ⇒ no-op scrub, never a crash
```

**Flow:** tolerate-missing JSON parse (`readJsonFile` catch → null) → pattern-validate entries → resolve pi's requestedSecrets to envVars (fail-closed on unknown names) → read values from THIS process env.
**Invariant:** values never touch disk in these files; malformed input degrades to an empty strip set rather than breaking the agent's bash tool.
**Probe:** `tests/read-localterm-secret-policy.test.ts` :79 hostile env var rejected, :51 unknown secret fail-closed, :23 both files absent ⇒ []; `tests/read-secret-values.test.ts` :50 floor-drop, :56 dedupe.

## Settings passthrough on tool override
**Path/Symbol:** `packages/pi-extension/src/utils/read-pi-shell-settings.ts:readPiShellSettings` (43–54).
**Data Shape:** merge global `~/.pi/agent/settings.json` + project `<cwd>/.pi/settings.json` (project wins); extract `shellPath` + `shellCommandPrefix` (non-empty strings only); both passed into `createBashToolDefinition(cwd, { operations, spawnHook, commandPrefix, shellPath })`.

**Invariant:** overriding the `bash` tool by name reconstructs it — omitting shellPath/commandPrefix silently loses the user's config.
**Probe:** `tests/read-pi-shell-settings.test.ts` :36 project overrides global, :60 empty string treated as unset.

**Honest limit:** both layers are defense-in-depth, NOT hard barriers — parent-process introspection (`ps eww $PPID` / `/proc/$PPID/environ`) or direct Keychain access still reaches keys; for untrusted agents don't wire secrets to the host process at all (source comment, bash-secret-scrub.ts:31–34).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "createStreamingRedactor|overlapTailLen|redactText|scrubEnv|readLocaltermSecretEnvVarsForPi", limit: 10 });
```
Graph check this session: redact trio resolved at redact-output.ts 60–82/33–46/10–20; scrubEnv 6–13 — line-exact vs HEAD f26c5853. A second `redactText` copy exists at `packages/server/src/utils/redact-output.ts:12-22` (daemon-side mirror).

## Verdict
Adopt the two-layer split (pure spawn-side scrub + streaming output redaction with full-value overlap hold-back), the length floor + fixed single-char mask, longer-values-first ordering, names-only policy files with canonical validation patterns, values-from-process.env, session_start recompute, lazy per-exec value reads, and settings passthrough; adapt the state-dir layout, patterns, and pi-extension wiring (BashSpawnHook/registerTool API) to your host; omit macOS Keychain specifics and the daemon mirror unless porting both packages. Tests run under vite-plus; probes cited from on-disk test files (tests excluded from the graph index by design).
