<!-- capsule-v2 -->
# NPM command parse-before-trust — how do you turn a pasted "npm install X" into a safe package spec without ever executing the command?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What is the rejection ladder that converts arbitrary user-pasted install commands into exactly one registry package spec — and what must NEVER be executed?

## Pure string parsing; anything ambiguous is a typed error, not a guess
**Path/Symbol:** `backend/python/app/services/skills/npm_command_parser.py:parse_npm_command/_strip_runner_prefix/_UNSAFE_CHARS_RE/_PACKAGE_SPEC_RE` (L27–123); frontend twin `frontend/app/(main)/workspace/skills/personal/npm-command-parser.ts` (UX preview only — backend is AUTHORITATIVE).
**Signature:** `parse_npm_command(raw: str) -> PackageSpec`; `PackageSpec(name: str, version: str = "latest")` frozen dataclass with `.registry_spec -> "name@version"`.
**Data Shape:** Accepts bare `name`, `@scope/name`, optional `@version|@tag`; runner prefixes stripped longest-first: `npx skills add, skills add, npm install -g, npm install, npm i -g, npm i, yarn global add, yarn add, pnpm add -g, pnpm add, npx`.

### Decisive source
```python
_UNSAFE_CHARS_RE = re.compile(r"[;&|`$(){}<>\"'\\\n\r]")
# Checked BEFORE any prefix stripping — a metachar anywhere in the paste
# rejects with "This looks like more than a single install command."

def _strip_runner_prefix(command):
    lowered = command.lower()                     # case-INSENSITIVE match,
    for prefix in _RUNNER_PREFIXES:               # but slice the ORIGINAL casing off
        if lowered.startswith(prefix + " ") or lowered == prefix:
            return command[len(prefix):].strip()
    return command

# Unrecognized-runner fallback: one leading word may be dropped ONLY if what
# remains is a single token not starting with '-' ("bun add foo" → foo);
# multi-word or flag-y remainders raise instead of guessing.

match = _PACKAGE_SPEC_RE.match(remainder.lower())  # spec itself lowercased
```
Module contract line 2: "PURE STRING PARSING, the command is NEVER executed." The parser's only output is a `PackageSpec`; the actual fetch goes through `SkillPackageImporter.preview_npm`, which hits `registry.npmjs.org/<name>/<version>` metadata JSON — the shell never sees user input.

**Flow:** empty → error · unsafe-char scan → error · longest-prefix strip (case-insensitive) → unrecognized-runner single-token salvage or error · empty/multi-token/flag-leading remainder → specific errors · regex-validate full spec (`@scope/name@version`) → lowercase → `PackageSpec(name, version or "latest")`.
**Invariant:** (1) Shell metacharacters are rejected BEFORE prefix logic so `npm install foo; curl evil` never reduces to a plausible-looking name. (2) Longest-prefix-first ordering prevents `npx skills add …` being chopped by bare `npx`. (3) Every failure carries a user-actionable message steering toward "paste just the package name" — errors are UX. (4) Version defaults to `"latest"` at the dataclass, not per call site. (5) A backend parser being authoritative over a frontend twin means validation lives server-side even when the client previews.
**Probe:** `tests/unit/services/skills/test_npm_command_parser.py` (151L): registry_spec default/explicit :13/:18; bare + scoped + versions :24–47; uppercase_normalized_to_lowercase :47; known_runner_prefixes param set :73; longest_prefix_wins_npx_skills_add_over_npx :86; unrecognized_runner_with_single_remaining_token :92; shell_metacharacters_rejected (parametrized) :121; multiple_packages_rejected :125; flag_only_rejected :133.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "parse_npm_command PackageSpec _strip_runner_prefix NpmCommandParseError" --detail ids
```

## Verdict
Adopt the reject-before-strip unsafe-char gate, longest-first case-insensitive prefix table slicing original casing, single-token salvage rule, and the typed-error-everywhere posture with zero execution. Adapt the runner table to the host ecosystem. Omit the frontend preview copy.
