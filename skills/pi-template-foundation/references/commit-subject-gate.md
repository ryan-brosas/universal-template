<!-- capsule-v2 -->
# Commit-subject gate — how do I mechanically enforce conventional-commit discipline over git history and PR titles in a manifest-free repo, and where does running two independent grammars bite?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** a porter adding commit/PR-title linting to a config-only agent-template repo must decide where the check runs, what it validates, and whether the CI title validator and the history validator can be allowed to disagree.

## Twin-grammar commit/PR-title validation plane
**Path/Symbol:** `scripts/conventional-commit.py:CONV_PAT` (:25), `check_subject` (:28-42), `main` (:45-67); twin grammar `.github/workflows/pr-title.yml:29-30`. (Line range :20-42 for the grammar, :45-67 for the driver.)
**Signature:** `check_subject(subject: str) -> list[str]`; `main() -> None` (exit 1 on violations).
**Data Shape:** input = raw commit subjects (`git log --pretty=%s -10`, run with `cwd=BASE` where `BASE = dirname(dirname(abspath(__file__)))` — the repo root, *not* the caller's cwd) or one PR title (argv). Output = violation strings accumulated into a **module-level** `errors` list; exit 0 prints `CONVENTIONAL COMMITS OK`, exit 1 prints each violation. Failure shape is fail-open: every `subprocess` exception is swallowed to `out = ""`, so an environment without git passes vacuously.

### Decisive source
```python
ALLOWED_TYPES = {
    "feat", "fix", "docs", "style", "refactor", "perf", "test", "chore",
    "ci", "build", "feat", "revert", "release", "wip",
}

CONV_PAT = re.compile(r"^(?P<type>[a-z]+)(\((?P<scope>[a-z0-9_\-]+)\))?!?:\s*(?P<desc>.+)$")

def check_subject(subject: str) -> list[str]:
    """Return a list of violations for a commit subject / PR title."""
    v = []
    m = CONV_PAT.match(subject.strip())
    if not m:
        v.append(f"not conventional (want '<type>(<scope>): <desc>', got '{subject.strip()}'")
        return v
    if m.group("type") not in ALLOWED_TYPES:
        v.append(f"unknown type '{m.group('type')}' (allowed: {sorted(ALLOWED_TYPES)})")
```

The regex accepts **any** lowercase `[a-z]+` word as type; `ALLOWED_TYPES` membership is a *separate second stage* whose error self-documents by printing `sorted(ALLOWED_TYPES)`. The set carries a harmless duplicate `"feat"` literal → 13 distinct types including non-standard `revert`, `release`, `wip`.

**Flow:** `main` → `git log --pretty=%s -10` at BASE (exception → empty output → zero checks) → per line: skip empty and any subject starting `"Merge "`/`"Revert "` → `check_subject` appends into module-level `errors` → exit 1 iff `errors`. Separately in CI, `pr-title.yml` interpolates `${{ github.event.pull_request.title }}` into a shell double-quoted variable (`title="..."`) then passes it as **argv** to an inline heredoc python whose regex hard-codes a 12-type alternation `(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert|release)` — no `wip`, and no description-capitalization/trailing-period checks.

**Invariant:** the two grammars are NOT cross-checked by any gate in the repo. Divergence is real and reachable: `wip: x` is a legal commit subject but fails the PR-title workflow; a new type requires editing both `ALLOWED_TYPES` and the pr-title alternation, and nothing detects forgetting one. Secondary hazards to preserve awareness of when porting: only the last 10 subjects are ever validated; the `"Revert "` prefix skip also spares hand-written subjects beginning "Revert "; module-level `errors` makes import-and-rerun accumulate stale violations; fail-open on missing git means the gate is silent-pass in sandboxes without git.

**Probe:** `.github/workflows/check.yml:48-51` (`python3 scripts/conventional-commit.py 2>&1 | tee /tmp/conventional-commit.log`). Executed live at the pin against the checkout's own history: **exit 1** exercising every violation class in one run — `unknown type 'records' | 'foundation' | 'turso'` (each printing the sorted 13-type allowed list, confirming the second-stage membership check and its self-documenting error), two `not conventional` regex rejects (`turso pass 15 …`, `awaithumans pass 5: …`), and `description should not start with a capital letter`. Wiring census (dotfile-aware): the script is referenced ONLY here — NOT in `.pre-commit-config.yaml`, whose local hooks are `repo-hygiene.py` + `check-circular-deps.py` alone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "conventional commit subject allowed types git log validate", limit: 10 });
// → scripts.conventional-commit.check_subject 28-42 (#1), .main 45-67
await mcp.codebase_memory.trace_path({ project: "pi-template", function_name: "check_subject", direction: "both" });
// → callers_total 2 (main ×1, module scope ×1); callees_total 1 (list.append)
```

## Verdict
Adopt the two-stage grammar (broad regex, then set-membership with a sorted-set error message) and the single-file driver shape that scopes `git log` to the script-derived repo root; adopt ONE shared validator for both history and PR titles so the type table cannot drift. Adapt the Merge/Revert skip into an explicit policy you actually want (prefix-skip is spoofable), bound or stream the history window deliberately, and make the errors container local to the run instead of module-level. Omit the twin inline heredoc grammar entirely (it is the anti-pattern this capsule documents), the fail-open exception swallowing if your CI guarantees git, and GitHub-specific event plumbing. Coverage caveat: no dedicated unit test exists for this script anywhere in the repo (the seven gate scripts ARE their own probe surface); graph coverage for all three cited paths returned `no_recorded_issue` / `metadata_match` at generation 2026-08-25T07:53:20Z.
