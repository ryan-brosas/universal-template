<!-- capsule-v2 -->
# Deprecated model shortcut shims — flag table mirrored across parser and handler with alias-aware warnings

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you keep old one-flag model shortcuts (`--4o`, `--sonnet`, `--35turbo`) working after the model catalog outgrew them, without hardcoding names twice inconsistently?

## Two tables that must stay in sync: add_argument definitions and a handler dict keyed by dest
**Path/Symbol:** `aider/deprecated.py`: `add_deprecated_model_args(parser, group)` (:1-83, 11 shortcuts incl. digit-leading flags `"--4"`, `"-4"`, `"--4o"`, `"--mini"`, `"--35turbo"/"--35-turbo"/"--3"/"-3"`), `handle_deprecated_model_args(args, io)` (:86-126); called from `main.py` :619 BEFORE env-var fallbacks.
**Signature:** handler iterates `model_map` (dest-style keys like `"4_turbo"`, `"o1_mini"`), converts `-`↔`_` to find `getattr(args, arg_name_clean)`, warns with the PREFERRED alias from `models.MODEL_ALIASES`, sets `args.model` only when unset, and `break`s after the first hit.
**Data Shape:** pinned snapshots: opus=`claude-3-opus-20240229`, sonnet=`anthropic/claude-3-7-sonnet-20250219`, haiku=`claude-3-5-haiku-20241022`, 4=`gpt-4-0613`, 4o-mini=`gpt-4o-mini`, turbo=`gpt-4-1106-preview`, deepseek=`deepseek/deepseek-chat`.

### Decisive source
```python
for arg_name, model_name in model_map.items():
    arg_name_clean = arg_name.replace("-", "_")
    if hasattr(args, arg_name_clean) and getattr(args, arg_name_clean):
        ...
        for alias, full_name in MODEL_ALIASES.items():
            if full_name == model_name:
                display_name = alias
                break
        io.tool_warning(f"The --{arg_name.replace('_', '-')} flag is deprecated ...")
        if not args.model:
            args.model = model_name
        break
```

**Flow:** parse → handle_deprecated_model_args resolves the FIRST matching shortcut into `args.model` (explicit `--model` wins) → downstream `select_default_model`/`Model()` see a normal model string. The warning teaches migration using whichever shorter alias exists, else the full name.
**Invariant:** precedence explicit-model > deprecated-shortcut > onboarding default; exactly ONE shortcut applies per run; the deprecation surface is intentionally frozen (dated snapshots) so old flags never silently retarget newer models.
**Probe:** direct tests executed GREEN this run via repo venv (`python -m pytest tests/basic/test_deprecated.py -q`: **3 passed, 26 subtests**): `test_deprecated_args_show_warnings` (:26), `test_model_alias_in_warning` (:76), `test_model_is_set_correctly` (:100). Deterministic: `grep -c 'add_argument' aider/deprecated.py` → 11.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "handle_deprecated_model_args", limit: 3 });
// rank-1: aider.aider.deprecated.handle_deprecated_model_args aider/deprecated.py 86-126
```

## Verdict
Adopt the two-table + alias-aware-warning pattern for any CLI carrying legacy option shims; adapt snapshot names. The first-hit-break semantics matter: porters who loop without break emit N warnings and nondeterministically pick the LAST shortcut instead of the first.
