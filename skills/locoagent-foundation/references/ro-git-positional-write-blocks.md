<!-- capsule-v2 -->
# Git positional write-blocks — which bare `git <sub> <word>` commands are actually writes wearing read-only clothes?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** `git tag`/`git branch`/`git reflog` pass flag validation with zero flags — how do you stop a positional argument from creating a ref or expiring history while still allowing list-mode patterns?

## Path/Symbol
**Path/Symbol:** `src/utils/shell/readOnlyCommandValidation.ts` — `'git reflog'` entry + `DANGEROUS_SUBCOMMANDS` callback (:270-304), `'git tag'` list-flag scanner (:712-806), `'git branch'` scanner with optional-arg tracking (:807-922), `'git remote show'`/`'git remote'` ordering note + callbacks (:472-502), `'git ls-remote'` excluded-flags comment (:312-340).
**Signature:** `additionalCommandIsDangerousCallback?: (rawCommand: string, args: string[]) => boolean` — args = tokens AFTER the command prefix.
**Data Shape:** Each callback re-walks args with its own local state: `flagsWithArgs: Set`, `flagsWithOptionalArgs` (branch only: `--merged`/`--no-merged`), `seenListFlag`, `seenDashDash`.

### Decisive source
```ts
// SECURITY: Block tag creation via positional arguments. `git tag foo`
// creates .git/refs/tags/foo (41-byte file write) — NOT read-only.
// ...
// `--` ends flag parsing. All subsequent tokens are positional args,
// even if they start with `-`. `git tag -- -l` CREATES a tag named `-l`.
if (token === '--' && !seenDashDash) {
  seenDashDash = true
  i++
  continue
}
```

**Flow:** validateFlags accepts all flags (positionals fall through as safe by default) → callback re-scans the same args → any non-flag positional BEFORE a `-l`/`--list` (or short bundle containing `l`) ⇒ dangerous; after `--` everything is positional (`git tag -- -l` CREATES `-l`); branch additionally treats positionals following `--merged`/`--no-merged` as their optional commit arg (safe); reflog blocks first-positional ∈ {expire, delete, exists} and allows `show`/ref names.

**Invariant:** (1) A positional for these commands is a WRITE (`git tag foo` = 41-byte `.git/refs/tags/foo`); the default positional fallthrough is wrong for exactly the commands whose positionals create refs. (2) `--` handling must match git: post-`--` tokens are NEVER flags — a validator that keeps treating `-l` as list-mode after `--` approves `git tag -- -l <target>` style writes. (3) Short bundles need char-level scanning: `-li` contains list mode; exact-match on '-l' misses it. (4) PARSE_OPT_OPTARG trap: `--abbrev N` detached is NOT consumed by git (becomes a branch name!) even though your validator consumes it — two-layer defense (validator type 'number' + callback not listing --abbrev in flagsWithArgs) so the callback sees N as an unsafe positional. (5) Map keys are prefix-matched longest-first; 'git remote show' MUST precede 'git remote'.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "DANGEROUS_SUBCOMMANDS = new Set(['expire', 'delete', 'exists'])" src/utils/shell/readOnlyCommandValidation.ts` → :291; `grep -nF "must come BEFORE 'git remote'" src/utils/shell/readOnlyCommandValidation.ts` → :472.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "additionalCommandIsDangerousCallback", limit: 5 });
// → BashTool readOnlyValidation tput variant :978-1045 + shared-map variants line-exact
// (the git tag/branch/reflog callbacks live INSIDE GIT_READ_ONLY_COMMANDS entries; cite file ranges directly)
```

## Verdict
Adopt the pattern: allowlist flags permissively but gate every write-capable positional behind a dedicated callback that models `--`, bundles, and optional-arg flags exactly like the binary. Adapt the command set to your host's CLIs. Omit nothing here if you port git at all — each callback documents a real write vector.
