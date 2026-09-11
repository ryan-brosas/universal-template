<!-- capsule-v2 -->
# Argv validation ladder — how do you build a CLI argv layer that fails fast with typed, actionable errors, separating tokenization, classification, applicability, conflicts, and config-aware conflicts into distinct gates?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A CLI with ~40 flags across 10 commands has a combinatorial error surface (unknown flags, missing values, flags in the wrong mode, mutually exclusive pairs, flags that conflict with config). How do you structure parsing so every failure is a stable machine-readable code with a human suggestion, and so "parse" never silently makes decisions that "validate" should reject loudly?

## Connected graph-selected seam
**Path/Symbol:** `src/cli/parse.ts:tokenizeArgv` (:135–220), `classifyCommand` (:406–494), `suggestSimilarFlag` (:73–95) + `levenshteinDistance` (:100–129), flag tables `FLAGS_WITH_VALUES`/`BOOLEAN_FLAGS` (:13–66); `src/cli/validate.ts:validateApplicability` (:76–224) with `DEEP_ONLY_FLAGS` (:13–34)/`SIMPLE_ONLY_FLAGS` (:67–70), `detectConflicts` (:237–347), `detectConfigConflicts` (:357–381); `src/cli/types.ts:CliValidationError` (:331–339) + 11-code `CliErrorCode` union (:341–353); pipeline `src/cli/index.ts:parseAndValidate` (:42–120); deprecated legacy twin `src/cli.ts:parseArgs` (re-exported at index.ts :393–396).
**Signature:** `tokenizeArgv(argv): { flags: RawFlags; positionals: string[] }`; `classifyCommand(positionals, flags): ParsedPositionals`; each gate throws `CliValidationError(message, code, suggestion?)`.
**Data Shape:** error taxonomy — `FLAG_REQUIRES_VALUE | INVALID_SESSION_ID | FLAG_NOT_APPLICABLE | MUTUALLY_EXCLUSIVE_FLAGS | ALIAS_BACKEND_MISMATCH | UNKNOWN_MODEL | INVALID_K_VALUE | UNKNOWN_COMMAND | MISSING_PROMPT | UNKNOWN_FLAG | AMBIGUOUS_PROMPT`. Session grammar: 1–64 chars of `[A-Za-z0-9._:-]`, resolved `-S` > `VEDA_SESSION` env > `'default'`, validated inside tokenize.

### Decisive source
```ts
// tokenizeArgv — value guard, -- separator, typed unknown-flag with suggestion:
if (FLAGS_WITH_VALUES.has(arg)) {
  const value = args[i + 1];
  if (value === undefined || value.startsWith('-')) {
    throw new CliValidationError(`Flag ${arg} requires a value`, 'FLAG_REQUIRES_VALUE');
  }
  parseFlagWithValue(flags, arg, value); i += 2; continue;
}
if (arg === '--') { positionals.push(...args.slice(i + 1)); break; }
if (arg.startsWith('-')) {
  const suggestion = suggestSimilarFlag(arg);   // Levenshtein ≤ 3, long-form only
  throw new CliValidationError(
    `Unknown flag: ${arg}`,
    'UNKNOWN_FLAG',
    suggestion
  );
}
// classifyCommand — "parse, don't validate": never joins positionals
case 'deep': {
  // Only accept single positional after 'deep'; 2+ will be rejected by validation
  const deepArgs = positionals.slice(1);
  return {
    command: 'prompt',
    args: [],
    prompt: deepArgs.length === 1 ? deepArgs[0] : undefined,
    subcommand: 'deep',  // Use subcommand to indicate deep mode
  };
}
// validateApplicability — ambiguous BEFORE missing, so the specific error wins:
if (isImplicitPrompt && positionals.length >= 2) {
  throw new CliValidationError(
    'Ambiguous prompt: multiple positional arguments',
    'AMBIGUOUS_PROMPT',
    'Did you mean to quote your prompt? Use: veda "your prompt here"'
  );
}
// ... (ambiguous checks for deep/resume commands, same code)
if ((isSimplePrompt || isDeepMode) && !parsed.prompt) {
  throw new CliValidationError(
    'No prompt provided',
    'MISSING_PROMPT',
    'Provide a prompt after the command or flags'
  );
}
// detectConflicts — listed-mode roster guards: -k may only confirm the list length
if (flags.k !== undefined && flags.k !== models.length) {
  throw new CliValidationError(
    `-k ${flags.k} conflicts with --solver-models (${models.length} models listed)`,
    'INVALID_K_VALUE',
    'Remove -k (roster size = list length) or repeat entries to duplicate models'
  );
}
```

**Flow:** `parseAndValidate`: (1) tokenize → (2) classify → (3) early returns for meta commands (help/version/init/guide/personas/sel/skills with subcommand allowlists, stats, models — models runs its own applicability gate first) → (4) `validateApplicability` (deep-only vs simple-only flag tables per command; models command rejects extra positionals, unknown backend ids, and any prompt-shaped flag) → (5) `detectConflicts` (mutual-exclusion pairs; the `--solver-models` listed-mode cluster: pins against `-m`/`--solver-model`/`--solver-backend(s)`/`--distribute-solvers`, rejects `--categories`, requires `--modules` length equality for positional zip, rejects sampling knobs, forces `k === list length`, caps at 12 entries) → (6) load global config → (7) `detectConfigConflicts` (deep only: `--solver-backend` vs config `distributeSolvers`, suppressed when the user explicitly passed `--distribute-solvers` OR pinned base `-b`/`-m`) → (8) resolve + construct the discriminated-union input.
**Invariant:** every failure is a `CliValidationError` with a stable code from the closed 11-code union plus an optional actionable suggestion (Levenshtein distance ≤ 3 computed over long-form flags only, dash-stripped); classification NEVER joins or guesses — multi-word prompts leave `prompt: undefined` and are rejected downstream as `AMBIGUOUS_PROMPT` with a quoting hint; ambiguous-prompt checks are ordered before missing-prompt so the more specific diagnosis wins; applicability tables (`DEEP_ONLY_FLAGS`/`SIMPLE_ONLY_FLAGS`) are the single source of mode-gating truth; the legacy twin `src/cli.ts:parseArgs` still ships `@deprecated` with its own flag table and post-`--` join-into-prompt behavior — it exists for backward compatibility, not as a second design.
**Probe:** `tests/cli/parse-validate.test.ts` (executed at pin: 59 pass / 1 fail under this host's real HOME — the one failure is environmental: an integration test asserts resolved backend ∈ {codex, claude-code, droid, pi} while the host's live `~/.config/veda/config` sets `BACKEND="agy"`; re-run with clean HOME gives **60 pass / 0 fail**) and `tests/cli.test.ts` (**33 pass / 0 fail**, legacy plane). Pinned behaviors: typo suggestion exactly `"Did you mean --solver-backend?"`; `AMBIGUOUS_PROMPT` suggestion contains `veda "your prompt here"`; `-k` range 1..12; flag-without-value and invalid-session throws; `--` literal-prompt escape; models gate (unknown backend, extra positionals, `-m` not applicable); conflict pairs incl. `--solver-backends requires --distribute-solvers`; config-conflict basePinned exception.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "tokenizeArgv classifyCommand validateApplicability detectConflicts CliValidationError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder: separate pure stages (tokenize → classify → applicability → conflicts → config-conflicts → resolve) where classification is total and decision-free, a closed error-code union with per-error suggestions, Levenshtein typo recovery bounded to long-form flags, ambiguous-before-missing ordering, and explicit applicability tables instead of scattered if-checks. Adapt the flag tables, codes, session grammar, and the 12-entry roster cap to your host. Omit the deprecated legacy twin when porting — do not replicate its post-`--` join-into-prompt semantics alongside the new plane; two tokenizers coexisting is migration debt, not a pattern. Porting hazards to keep: the value guard rejects ANY value starting with `-` (dash-prefixed ids must go after `--`), and config-aware conflicts must check "did the user explicitly override" before firing, or they will reject valid explicit control.
