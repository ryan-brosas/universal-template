<!-- capsule-v2 -->
# Shell env denylist: prefix globs strip provider credentials from the child environment — opt-in, not a boundary

## Source / Question
`pydantic_ai_harness/shell/_capability.py:14–110` @ `main@f971198` (PR #9989 "harden capability defaults") — Agents spawn shell commands that inherit every provider API key in the parent environment. How do you offer credential stripping WITHOUT silently breaking agents that rely on inherited creds, and how must the docs word its limits?

## Path / Symbol
`shell/_capability.py` — `_DEFAULT_DENIED_COMMANDS` tuple (:14–25), `LLM_API_KEY_ENV_PATTERNS` (:28–47), `Shell.__post_init__` allow/deny interlock (:107–110), new fields `env` (:86–94) + `denied_env_patterns` (:96–105) forwarded in `get_toolset` (:112–125).

## Signature
```python
LLM_API_KEY_ENV_PATTERNS: tuple[str, ...] = (
    'ANTHROPIC_*', 'GATEWAY_*', 'GEMINI_*', 'GOOGLE_*', 'OPENAI_*', 'OPENROUTER_*',
    'PYDANTIC_AI_GATEWAY_API_KEY',
)
denied_commands: Sequence[str] = _DEFAULT_DENIED_COMMANDS     # class-level sentinel default
def __post_init__(self):
    if self.denied_commands is _DEFAULT_DENIED_COMMANDS:      # IDENTITY check, not ==
        self.denied_commands = [] if self.allowed_commands else list(_DEFAULT_DENIED_COMMANDS)
```

## Data Shape
`denied_env_patterns` matches by fnmatch GLOB because "env secrets cluster by prefix — unlike `denied_commands`, which matches executable names exactly" (:99–101). Applied ON TOP of an explicit `env` mapping too (:102–104). `LLM_API_KEY_ENV_PATTERNS` is a ready-made constant to pass, NOT applied automatically.

### Decisive source
Docstring honesty contract (:39–46): "This is not a security boundary: a command running under the same OS identity may still read the parent process's environment through system interfaces such as Linux procfs. Use OS-level isolation for untrusted commands… the prefixes are coarse (`GOOGLE_*` also strips `GOOGLE_APPLICATION_CREDENTIALS`)… Not a default: stripping env silently would break agents that rely on inherited credentials, so opt in explicitly." Same wording repeated on the `env` replacement field (:91–93).

**Flow:** user passes `denied_env_patterns=LLM_API_KEY_ENV_PATTERNS` → toolset strips matching names from the base env before spawn → command sees no provider keys but procfs remains readable to same-UID processes.
**Invariant:** identity-sentinel default resolution lets an explicit empty denylist disable the built-in destructive-command block while a bare constructor keeps it; never claim security-boundary status for same-user stripping.

## Probe (direct test)
`tests/shell/test_shell.py` — env-strip matrix (patterns remove `OPENAI_API_KEY` from spawned env; explicit `env` also filtered; absent patterns inherit untouched). Construction interlock: allowed_commands non-empty empties the default denylist (:109–110).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'LLM_API_KEY_ENV_PATTERNS denied_env_patterns'
```

## Verdict
**Adopt** opt-in glob denylist + honest not-a-boundary doc wording for any subprocess capability. **Adapt** the pattern list to your providers. **Omit** nothing.
