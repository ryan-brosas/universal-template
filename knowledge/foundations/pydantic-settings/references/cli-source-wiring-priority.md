<!-- capsule-v2 -->
# CLI source wiring — how does a CLI source join a settings pipeline, and where does it rank?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** I'm adding a command-line source to a layered settings pipeline without breaking non-CLI usage — how is it gated, and does it outrank env vars or init kwargs?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/main.py:_settings_init_sources` (363-496) — the same builder that assembles every other source.
**Signature:** `cli_parse_args: bool | list[str] | tuple[str, ...] | None = None` (None ⇒ no CLI source at all)
**Data Shape:** `sources` tuple where element order = priority (first wins); CLI is prepended *ahead of init*.

### Decisive source
```python
custom_cli_sources = [source for source in sources if isinstance(source, CliSettingsSource)]
if not any(custom_cli_sources):
    if isinstance(cli_settings_source, CliSettingsSource):
        sources = (cli_settings_source,) + sources
    elif cli_parse_args is not None:
        cli_settings = CliSettingsSource[Any](cls, ..., _env_settings_source=env_settings)
        sources = (cli_settings,) + sources
# We ensure that if command line arguments haven't been parsed yet, we do so.
elif cli_parse_args not in (None, False) and not custom_cli_sources[0].env_vars:
    custom_cli_sources[0](args=cli_parse_args)
```
Default rank becomes **CLI > init kwargs > env > dotenv > secrets > defaults** because the fold merges
`deep_update(newer_state, older_state)` with the earlier tuple element on top (see `source-priority-pipeline`).

**Flow:** Resolve all `cli_*` config keys (kwarg beats model_config) → build the four standard sources →
let `settings_customise_sources` run → append defaults → three-way CLI gate: a user-supplied
`CliSettingsSource` instance inside the customized tuple is used as-is; else a `cli_settings_source`
override instance is prepended; else `cli_parse_args is not None` builds one and prepends it. If a custom
CLI source already exists but hasn't parsed yet (`env_vars` empty) and parsing was requested, it is parsed
eagerly right here. Unprovided flags are argparse-`SUPPRESS`ed (`CLI_SUPPRESS`, cli.py:297), so an absent
flag contributes nothing and lower sources win by default — precedence only materializes for explicitly
given flags.

**Invariant:** `cli_parse_args=None` (the default) means zero CLI participation; enabling it never changes
which sources exist, only what sits in front. The eager-parse latch (`not .env_vars`) makes "parse once"
idempotent across re-entry. The `_env_settings_source` reference passed to the constructor is used only
for `cli_show_env_vars` help text — the CLI source never reads os.environ itself.
**Probe:** `python3 -m pytest tests/test_source_cli.py -k test_cli_app_run_env_file_from_model_config -p no:cacheprovider -q` — EXECUTED PASSING; tests/test_source_cli.py:3852-3870 proves CliApp.run still drives the full pipeline (env_file honored under a CLI run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "settings init sources cli parse args prepend", limit: 10 });
```

## Verdict
Adopt the gate ladder (opt-in flag → override instance → customizer instance) and prepend-ahead-of-init
ordering with SUPPRESS-based silence. Adapt the priority position to your host's contract if CLI must lose
to init kwargs. Omit the `_env_settings_source` help-text plumbing unless you mirror help output.
