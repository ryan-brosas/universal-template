<!-- capsule-v2 -->
# validator-fail-loud-message-ladder — how does a zero-dependency validator fail first with a message that names the fix?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** How do I structure a package-consistency checker so every failure is self-explanatory and no check can pass silently after a partial parse?

## Linear module-level gate pipeline with one fail-loud helper
**Path/Symbol:** `scripts/validate-package.py:require_match` (:19–22) + its module-scope call sites (:25, :34); the whole pipeline is 88 lines, top-to-bottom, no functions besides the helper.
**Signature:** `def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]`
**Data Shape:** Input: an optional regex match plus a pre-written failure message. Output: the non-None match (unwrapped for `.group()` chaining). Failure shape: `SystemExit(message)` — Python prints the string to stderr and exits 1; no traceback, no error class hierarchy, no retries.

### Decisive source
```python
def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]:
    if match is None:
        raise SystemExit(message)
    return match
```
(:19–22. Every regex gate wraps its match in this before touching `.group()`, so a missing pattern can never surface as `AttributeError: 'NoneType'`.)

**Flow:** load all five package files at module scope (:11–16, `Path(__file__).resolve().parent.parent` makes it cwd-independent; docstring :2 declares "without external dependencies") → gates run strictly in order, each either passing silently or killing the process: frontmatter extraction → banned-field scan → version parity → skill-file layout → plain-language rules → SKILL numbering → README table coverage → 500-line budget → success sentinel `print(f"Humanizer package v{skill_version} is valid")` (:88).

**Invariant:** The message grammar is imperative and fix-naming — "Add metadata.version to SKILL.md", "Remove unsupported YAML field", "Use one package version in all files: [...]", "Keep one regular SKILL.md at the repo root", "Point the Claude plugin skill loader at the repo root", "Add the missing Plain Language rules to AGENTS.md: ...", "Number SKILL.md patterns from 1 through 35: [...]". A failing run always ends with the next action, never a bare assertion. Fail-first ordering means the earliest broken invariant is the only diagnostic — acceptable because each gate is cheap and deterministic.

**Probe:** Executed GREEN path this pass: `python3 scripts/validate-package.py` from the checkout root → stdout `Humanizer package v2.11.2 is valid`, exit code 0 (the command AGENTS.md "Rules for changes → Checks" names). RED-via-mutation was NOT executed — the source checkout is read-only for mining lanes and no file may be created or rewritten; failure semantics are established from the require_match source plus Python `SystemExit(str)` behavior and recorded here as a deterministic-content probe, not fabricated as an executed failure.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", name_pattern: "require_match", fields: ["signature", "lines"] })
```

## Verdict
Adopt require_match-style unwrapping (never chain `.group()` on an optional match), SystemExit-with-string as the whole error-reporting mechanism for CI validators, imperative fix-naming messages, and a single sentinel success line that echoes the checked version. Adapt gate count/order and message wording per repo. Omit exception classes/exit-code taxonomies — deliberately absent here because GitHub Actions only needs exit status and the log line.
