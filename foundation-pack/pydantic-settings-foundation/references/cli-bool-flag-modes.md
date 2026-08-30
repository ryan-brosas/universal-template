<!-- capsule-v2 -->
# CLI bool flag modes — how are boolean fields exposed as flags (explicit vs dual vs toggle)?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** Booleans are the classic CLI footgun (`--flag true`? `--flag`? `--no-flag`?) — what exact ladder maps a `bool` field to flag actions?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/cli.py:_convert_bool_flag` (1202-1224) + `'no-'` prefix flip in `_add_parser_args` (1186-1187); sentinels `_CliImplicitFlag`/`_CliToggleFlag`/`_CliDualFlag`/`_CliExplicitFlag` in `sources/types.py` (61-74).
**Signature:** `_convert_bool_flag(self, kwargs: dict[str, Any], field_info: FieldInfo, model_default: Any) -> None`
**Data Shape:** mutates the argument kwargs: deletes `metavar`, sets `action` to `BooleanOptionalAction`, `store_true`, or `store_false`.

### Decisive source
```python
if kwargs['metavar'] == 'bool':
    meta_bool_flags = [meta for meta in field_info.metadata
                       if isinstance(meta, type) and issubclass(meta, _CliImplicitFlag | _CliExplicitFlag)]
    if not meta_bool_flags and self.cli_implicit_flags:
        meta_bool_flags = [_CliImplicitFlag]            # global mode promotes plain bools
    if meta_bool_flags:
        bool_flag = meta_bool_flags.pop()
        if bool_flag is _CliImplicitFlag:
            bool_flag = (_CliToggleFlag if self.cli_implicit_flags == 'toggle'
                         and isinstance(field_info.default, bool) else _CliDualFlag)
        if bool_flag is _CliDualFlag:
            del kwargs['metavar']; kwargs['action'] = BooleanOptionalAction   # --x / --no-x both accepted
        elif bool_flag is _CliToggleFlag:
            del kwargs['metavar']
            kwargs['action'] = 'store_false' if field_info.default else 'store_true'
```
And in registration: `if arg.kwargs.get('action') == 'store_false': flag_prefix += 'no-'` — the negative
form gets the `--no-` name; the positive form stays bare.

**Flow:** Field-level annotations always beat the global `cli_implicit_flags` config. Four exposure modes:
plain bool with no mode ⇒ value-taking argument (`--flag True`); `CliExplicitFlag[bool]` ⇒ same regardless
of mode; dual (`True`/`'dual'` or `CliDualFlag[bool]`) ⇒ argparse `BooleanOptionalAction` accepting both
`--flag` and `--no-flag`; toggle (`'toggle'` on a defaulted bool, or `CliToggleFlag[bool]`) ⇒ a single
bare flag aligned with the default (`default=False` → `store_true --flag`; `default=True` →
`store_false --no-flag`). Required booleans stay dual even under `'toggle'`.
**Invariant:** Metadata annotation wins over config; toggle's single flag encodes "the non-default
direction" so passing it always changes the value. Serialization round-trips: `CliApp.serialize`
re-emits exactly the flags that were passed (test asserts `serialized_args == flag_args`).
**Probe:** `python3 -m pytest tests/test_source_cli.py -k test_cli_bool_flags -p no:cacheprovider -q` — EXECUTED PASSING (4 passed, parametrized over `None/True/'dual'/'toggle'`); tests/test_source_cli.py:2128-2137 proves dual accepts a bare required flag and serializes round-trip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "convert bool flag implicit dual toggle store", limit: 10 });
```

## Verdict
Adopt the precedence ladder (field annotation > global mode > default explicit-value) and the
"default-aligned single flag" trick for toggles. Adapt `BooleanOptionalAction` to your parser library's
flag-pair idiom; omit serialization parity unless you need replay.
