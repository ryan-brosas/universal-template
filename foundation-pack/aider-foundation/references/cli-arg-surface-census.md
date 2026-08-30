<!-- capsule-v2 -->
# CLI arg surface census — 945-line configargparse declaration as the single options contract

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** What does the FULL user-facing configuration surface look like, and which declaration-time tricks bind YAML config files, env vars, and shell completion into one grammar?

## One get_parser(); every flag is simultaneously a --cli-flag, an AIDER_* env var, and a yaml key; edit-format choices derived live from the coder registry
**Path/Symbol:** `aider/args.py`: `resolve_aiderignore_path(path_str, git_root=None)` (:22, relative aiderignore paths anchor to GIT ROOT not cwd — load-bearing for monorepos), `default_env_file(git_root)` (:31), `get_parser(default_config_files, git_root)` (:35-945), shtab completion attachments (`group.add_argument("files", ...).complete = shtab.FILE` :58), deprecated group via `add_deprecated_model_args` (:17 import).
**Signature:** parser constructed with `add_config_file_help=True, default_config_files=..., config_file_parser_class=configargparse.YAMLConfigFileParser, auto_env_var_prefix="AIDER_"` — so `--map-tokens` ≡ env `AIDER_MAP_TOKENS` ≡ yaml key `map-tokens:`.
**Data Shape:** ~200 declared options across groups (Main model / Output settings / History / Git / Lint+test / Analytics / Upgrading / Modes); `--config` itself is `is_config_file=True` (:791).

### Decisive source
```python
parser = configargparse.ArgumentParser(
    description="aider is AI pair programming in your terminal",
    add_config_file_help=True,
    default_config_files=default_config_files,
    config_file_parser_class=configargparse.YAMLConfigFileParser,
    auto_env_var_prefix="AIDER_",
)
# Dynamically gather them from the registered coder classes so the list
# stays in sync if new formats are added.
from aider import coders as _aider_coders
edit_format_choices = sorted({c.edit_format ...})
...
type=lambda path_str: resolve_aiderignore_path(path_str, git_root),   # :429
```

**Flow:** args.py is consumed three ways at runtime: main.py builds parsers twice (bootstrap capsule), `get_sample_yaml()/get_md_help()` (:885/:872) render the SAME declarations into docs artifacts via args_formatter classes (YamlHelpFormatter/MarkdownHelpFormatter/DotEnvFormatter), and shtab emits shell completions — one grammar, four projections.
**Invariant:** any porter who re-declares options outside this file breaks the yaml/env/cli trinity; the aiderignore path-type lambda is the only place git-root context enters parsing, and forgetting it strands relative ignore paths when cwd ≠ root.
**Probe:** deterministic anchors: `grep -nF 'auto_env_var_prefix' aider/args.py` → exactly :41; `grep -c 'add_argument' aider/args.py` → 199. Direct tests: `tests/basic/test_main.py` exercises flag plumbing end-to-end (executed green within the basic-suite run).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "resolve_aiderignore_path", limit: 3 });
// rank-1: aider.aider.args.resolve_aiderignore_path aider/args.py 22-28
```

## Verdict
Adopt configargparse's trinity pattern (yaml+env+flag from one declaration) for any config-heavy agent CLI; adopt the derived-choices + path-anchoring tricks verbatim. OMIT mining per-option help text — it's product copy, not architecture; the grammar shape is the seam.
