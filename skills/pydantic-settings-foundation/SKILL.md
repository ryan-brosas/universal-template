---
name: pydantic-settings-foundation
description: Use when porting layered settings/config resolution machinery — ordered settings-source pipelines, env-var field resolution with aliases, nested-delimiter explosion of complex values, .env extra harvesting, secret-dir scanning, alias-aware JSON/TOML/YAML config file sources, or argparse-style CLI settings sources with repeated-flag merging, bool flag modes, and subcommand app runtimes from pydantic-settings.
---

# pydantic-settings: settings-source resolution foundation

## Use this for
Use when porting multi-source configuration resolution (init > env > dotenv > secrets > defaults),
building pluggable config providers over a typed model class, or reimplementing env parsing for
nested models. Source code and direct tests are ground truth; references carry decisive excerpts
and graph retrieval.

## Load the matching source dump
- `references/source-priority-pipeline.md` — how are sources ordered and folded so earlier sources win?
- `references/current-state-visibility.md` — how do custom sources coordinate during one resolution?
- `references/env-field-resolution.md` — which env var names map to which field key, in what precedence?
- `references/complex-env-value-pipeline.md` — JSON decode vs delimiter explode vs plain string?
- `references/dotenv-extras-contract.md` — what happens to .env vars matching no declared field?
- `references/secrets-dir-contract.md` — how are secret dirs scanned, ordered, and decoded?
- `references/file-config-sources.md` — how do JSON/TOML/YAML sources get alias-aware keys?
- `references/cli-source-wiring-priority.md` — how does a CLI source join the pipeline and where does it rank?
- `references/cli-parser-adapter-inheritance.md` — how does a CLI source reuse the env pipeline and drive any parser?
- `references/cli-field-arg-descriptor.md` — how does one typed field become exactly one parser argument?
- `references/cli-parsed-list-merge.md` — what happens when one flag is repeated/comma/JSON/k=v?
- `references/cli-bool-flag-modes.md` — how are booleans exposed as explicit/dual/toggle flags?
- `references/cli-app-subcommand-runtime.md` — how does a model run as an app with subcommands and async commands?

## Capsule map
- **Priority fold** — `source-priority-pipeline`: tuple order = priority; fold is `deep_update(source_state, state)` so the *earlier* source is merged on top; defaults appended last then stripped when equal.
- **Source coordination** — `current-state-visibility`: every source receives the accumulated state of all higher-priority sources immediately before its `__call__`.
- **Env name ladder** — `env-field-resolution`: `_extract_field_info` yields `(field_key, env_name, value_is_complex)` triples; validation_alias choices beat field name; first env hit wins.
- **Complex value pipeline** — `complex-env-value-pipeline`: complex fields JSON-decode the single value AND delimiter-explode sibling vars, then deep-merge both.
- **Dotenv extras** — `dotenv-extras-contract`: unmatched prefixed vars become stripped extras only when `extra != 'forbid'`; delimiter-boundary guard prevents prefix collisions like `dbx_token`.
- **Secrets scanning** — `secrets-dir-contract`: missing dir warns + skips, non-dir raises `SettingsError`, later dirs override earlier, files read as UTF-8 and stripped.
- **File providers** — `file-config-sources`: Json/Toml/Yaml sources are `InitSettingsSource + ConfigFileSourceMixin`, inheriting alias-aware init-kwarg normalization.
- **CLI wiring** — `cli-source-wiring-priority`: opt-in gate ladder (`cli_parse_args` → override instance → customizer instance); CLI is prepended ahead of init (explicit flags beat everything; argparse-SUPPRESS silence defers to lower sources).
- **CLI parser adapter** — `cli-parser-adapter-inheritance`: `CliSettingsSource` subclasses `EnvSettingsSource` (delimiter `.`, prefix, enum parsing) and drives any argparse-like host via six injected parser methods; one decode path through `parse_env_vars`.
- **CLI field descriptor** — `cli-field-arg-descriptor`: `_CliArg` self-registers into a dual-keyed `parser_map` with cached classifiers (`subcommand_dest`, `is_append_action`, `is_no_decode`); non-outermost sentinels raise.
- **CLI merge engine** — `cli-parsed-list-merge`: repeated flags fold to first-token (str), reserialized `[...]` (list), or update-merged JSON object (dict) via a declared→inferred type fallback tokenizer.
- **CLI bool modes** — `cli-bool-flag-modes`: field annotation beats global mode; dual = `BooleanOptionalAction`, toggle = single default-aligned `store_true/store_false` flag with `--no-` naming.
- **CliApp runtime** — `cli-app-subcommand-runtime`: identity-keyed subcommand stack with finally-cleanup, optional-root/required-subcommand `cli_cmd`, thread-isolated async dispatch, per-subcommand unknown-arg scoping.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pydantic-settings (MIT), `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory project `pydantic-settings` (FULL mode, generation 2026-08-25T20:07:09Z, 1200 nodes / 5203 edges, no parse-partial, no skipped files; excluded by design: `.git/`, two docs images). Pass 1 covered the resolution kernel (7 capsules); Pass 2 covered the CLI plane (6 capsules): `sources/providers/cli.py`, main.py CLI wiring + `CliApp`, sentinel types in `sources/types.py`, `get_subcommand` in `sources/base.py`. Cloud secret providers uncited.

## Full view (memory graph)
Revalidate `pydantic-settings` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure source-priority fold and per-field resolution contracts (they are host-independent); adapt the pydantic-coupled pieces (`model_fields`, `FieldInfo`, `TypeAdapter`, `pydantic._internal._utils.deep_update`) to your model layer; the argparse-backed CLI contracts port as adapter patterns (inject your parser's method handles), while vendor-specific secret-manager clients remain out of scope unless porting those subsystems deliberately.
