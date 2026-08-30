<!-- capsule-v2 -->
# Four-pass slash arg substitution — how do you expand $name/$N/$ARGUMENTS in a skill body so no pass can re-scan another's output?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is Claude-Code-style argument substitution implemented so substituted values are never recursively expanded and undeclared `$word` text stays unharmed?

## One tokenizing pass, alternation order = precedence
**Path/Symbol:** `src/cuga/backend/slash_commands/arg_substitution.py:36-49` (`_TOKEN_RE`), `substitute` (:92-138), `validate_arg_names` (:60-77), `split_args` (:80-86).
**Signature:** `substitute(body: str, raw_args: str, arg_names: Sequence[str] = ()) -> str`; `validate_arg_names(names: Sequence[str]) -> None`; `split_args(raw_args: str) -> List[str]`.
**Data Shape:** Named args bind positionally (i-th declared name ← i-th positional from `shlex.split`, quote-aware with naive-split fallback); missing positional ⇒ empty string; `\\$` ⇒ literal `$`.

### Decisive source
```python
# arg_substitution.py:36-44 — the alternation order encodes the four-pass
# precedence: escaped → indexed → bare → named → positional. One regex pass:
_TOKEN_RE = re.compile(r"""
  (?P<escaped>\\\$)
| (?P<indexed>\$ARGUMENTS\[(?P<idx>\d+)\])
| (?P<bare>\$ARGUMENTS\b)
| \$(?P<named>[A-Za-z_][A-Za-z0-9_]*)
| \$(?P<pos>\d+)
""", re.VERBOSE)
```
The single-pass property is the whole safety argument (module docstring): each body position matches exactly one token form, so a value inserted by one "pass" can never be rescanned by a later one — no recursive expansion, no `$1` inside a substituted value blowing up. An UNDECLARED named token (`$word` not in `arg_names`) returns `m.group(0)` verbatim — skill bodies containing literal `$` prose are unharmed. `found_placeholder` tracks whether ANY recognized placeholder fired; if none did and args were supplied, the args append as a trailing `\n\nARGUMENTS: <raw>` line.

**Flow:** registration time: `validate_arg_names` rejects numeric-only names (`$1` collides with positional syntax) and reserves the name `ARGUMENTS` — a bad declaration fails the skill, not a run. Runtime: split → build named map → `_TOKEN_RE.sub(repl)` → append-fallback.
**Invariant:** Substitution must be non-rescanning (single tokenizing pass over the ORIGINAL body) and must leave undeclared `$tokens` untouched; numeric arg names can never be legal because they collide with `$N`.

**Probe:** `tests/unit/test_slash_arg_substitution.py::test_positional_substitution_is_one_indexed / test_positional_zero_is_empty / test_split_args_honors_quotes / test_validate_arg_names_rejects_numeric_only` — pins indexing, out-of-range emptiness, quote handling, and name validation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "arg_substitution substitute ARGUMENTS placeholder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-tokenizing-pass design with alternation-encoded precedence, verbatim passthrough for undeclared names, and the append-if-no-placeholder fallback. Adapt token spellings to your template syntax. Omit shlex fallback only if you never take quoted args. Direct tests exist.
