<!-- capsule-v2 -->
# CLI field→argument descriptor — how does one typed field become exactly one parser argument?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** How do I map model fields onto parser arguments while classifying subcommands, positionals, append-collections, aliases, and decode suppression?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/cli.py:_CliArg` (137-291) + `_add_parser_args` (1024-1194) + sentinels in `sources/types.py` (53-78).
**Signature:** `_CliArg(field_info: FieldInfo, parser_map: defaultdict[str | FieldInfo, dict[int | str | type | None, _CliArg]], **values)` (a pydantic model)
**Data Shape:** `parser_map` is dual-keyed: dest-string → `{alias-index|None → arg}` AND `FieldInfo → the same objects`; alias-path dests get per-index copies.

### Decisive source
```python
self._alias_names, self._is_alias_path_only = _get_alias_names(self.field_name, self.field_info,
    alias_path_args=self._alias_paths, case_sensitive=..., populate_by_name=...)
if self.subcommand_dest:
    for sub_model in self.sub_models:
        parser_map[self.subcommand_dest][sub_model] = ...
elif self.dest not in alias_path_dests:
    parser_map[self.dest][None] = self
    parser_map[self.field_info][None] = parser_map[self.dest][None]

@cached_property
def dest(self) -> str:
    if (not self.subcommand_dest and self.arg_prefix
            and self.field_info.validation_alias is not None and not self.is_parser_submodel):
        return f'{self.arg_prefix}{self.preferred_alias}'[self.env_prefix_len:]
    return f'{self.arg_prefix}{self.preferred_alias}'
```
Classification cached-properties: `subcommand_dest = f'{prefix}:subcommand'` iff `_CliSubCommand` in
field metadata; `is_append_action` = annotation contains list/set/dict/Sequence/Mapping;
`is_parser_submodel` = nested models without append action; `is_no_decode` = `NoDecode` metadata or
`enable_decoding=False` unless `ForceDecode`. Non-outermost `CliSubCommand`/`CliPositionalArg`
annotations raise SettingsError (244-251).

**Flow:** `_add_parser_args` sorts fields (`_sort_arg_fields`, required/discriminators first), builds a
`_CliArg` per field, then branches: subcommand fields create subparsers and recurse with dotted
`arg_prefix=f'{dest}.'`; everything else registers with `kwargs['default'] = CLI_SUPPRESS`
(= argparse SUPPRESS, so unprovided args never enter the namespace), `required` only under
`cli_enforce_required`, then conversion ladders append → positional → bool. A `model_path` set guards
recursive model cycles; AliasPath arguments are added last (`_add_parser_alias_paths`). Public wrappers:
`CliSubCommand = Annotated[T | None, _CliSubCommand]`, `CliPositionalArg = Annotated[T, _CliPositionalArg]`,
plus `_CliUnknownArgs` for tolerated-unknown buckets.
**Invariant:** One field ⇒ at most one registered argument (dupes skipped via `added_args`); dest paths are
dot-joined so parsed output nests through the inherited env delimiter explosion; positional conversion
drops `dest`/`required` kwargs and sets nargs `+`/`*`/`?` from field requiredness.
**Probe:** `python3 -m pytest tests/test_source_cli.py -k test_cli_alias_subcommand_and_positional_args -p no:cacheprovider -q` — EXECUTED PASSING; tests/test_source_cli.py:239-286 exercises alias + subcommand + positional classification together.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "CliSubCommand CliPositionalArg add parser args sort fields", limit: 10 });
```

## Verdict
Adopt the descriptor-object pattern: build a per-field record that self-registers into a dual-keyed map
(name-keyed for parsing, FieldInfo-keyed for lookup), with classification as cached properties derived
from annotation metadata. Adapt sentinel vocabulary to your host; omit discriminator sorting if your models
have none.
