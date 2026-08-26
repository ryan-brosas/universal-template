<!-- capsule-v2 -->
# CLI parser adapter — how does a CLI source reuse the env pipeline and drive any parser?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** How can one settings source emit arguments into argparse *or any other* parser library, and how do parsed values get decoded?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/cli.py:CliSettingsSource.__init__` (354-497) — class declaration at 302: `class CliSettingsSource(EnvSettingsSource, Generic[T])`.
**Signature:** `__init__(..., root_parser=None, parse_args_method=None, add_argument_method=ArgumentParser.add_argument, add_argument_group_method=..., add_parser_method=_SubParsersAction.add_parser, add_subparsers_method=..., format_help_method=...)`
**Data Shape:** parsed output is normalized to `dict[str, list[str] | str]` (dest → raw string tokens) before decoding.

### Decisive source
```python
super().__init__(
    settings_cls,
    env_nested_delimiter='.',
    env_parse_none_str=self.cli_parse_none_str,
    env_parse_enums=True,
    env_prefix=self.cli_prefix,
    case_sensitive=case_sensitive,
    env_nested_max_split=0,
    _init_state=_init_state,
)
root_parser = _CliInternalArgParser(cli_exit_on_error=self.cli_exit_on_error, prog=...,
                                    allow_abbrev=False, add_help=False, ...) if root_parser is None else root_parser
self._connect_root_parser(root_parser=root_parser, parse_args_method=..., ...)
...
self.env_vars = parse_env_vars(cast(Mapping[str, str], parsed_args), self.case_sensitive,
                               self.env_ignore_empty, self.cli_parse_none_str)
```

**Flow:** The class inherits the entire pass-1 env pipeline by subclassing `EnvSettingsSource` with
re-tuned knobs: the CLI's dotted dest paths (`a.b.c`) are exploded by `env_nested_delimiter='.'`, the
optional `cli_prefix` becomes `env_prefix`, enum member names are always parsed. After parsing, the
namespace dict is fed through the *same* `parse_env_vars` used for environment variables — there is no
second decode path. Parser access is funneled through six injected method references, so click-like or
custom parsers work if they honor argparse attribute names (`_connect_root_parser`, 953-1005). The default
parser is `_CliInternalArgParser` which converts argparse errors into `SettingsError` unless
`cli_exit_on_error=True` → `SystemExit(2)`; abbreviations are disabled (`allow_abbrev=False`) and
case-insensitive flag matching is only supported on this internal parser (SettingsError otherwise).
Parsing happens eagerly in the constructor when `cli_parse_args ∉ (None, False)` (`True` ⇒ `sys.argv[1:]`),
and `__call__` (537-554) is dual-contract: explicit `args=`/`parsed_args=` returns the source itself
(mutating its `env_vars`) while the pipeline's bare call delegates to `super().__call__()` and returns the
dict.
**Invariant:** Exactly one decode path (`parse_env_vars`); `cli_parse_none_str` defaults to `'null'`
(JSON) or `'None'` under `cli_avoid_json`; prefix validation rejects non-dotted-identifier prefixes with
SettingsError before any argument exists.
**Probe:** `python3 -m pytest "tests/test_source_cli.py::test_cli_dummy_user_settings_with_subcommand[cfg]" -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); tests/test_source_cli.py:2632+ drives CliSettingsSource through `CliDummyParser`, a non-argparse parser double, proving the adapter seam.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "CliSettingsSource root parser connect parse env vars", limit: 10 });
```

## Verdict
Adopt subclassing your simplest existing source (env-like) and re-entering its decoder with reshaped
input, plus method-injection for foreign parser hosts. Adapt delimiter/prefix knobs to your naming scheme;
omit `_CliInternalArgParser`'s exit-on-error duality if your host has its own error channel.
