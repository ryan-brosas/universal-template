<!-- capsule-v2 -->
# CLI repeated-flag merge engine — what happens when one flag is repeated, comma-separated, JSON-arrayed, or k=v'd?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** argparse `action='append'` gives me a list of raw strings — how do I fold that into one value per field annotation (str / list / dict)?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/cli.py` — `_resolve_parsed_args` (628-657), `_get_merge_parsed_list_types` (682-697), `_merge_parsed_list` (729-772), `_merged_list_to_str` (699-727).
**Signature:** `_merge_parsed_list(self, parsed_list: list[str], field_name: str) -> str`
**Data Shape:** input = one dest's accumulated occurrences; output = a single string the env pipeline decodes (`first token`, `[a,b,c]`, or a JSON object dump).

### Decisive source
```python
while val:
    val = val.strip()
    if val.startswith(','):
        val = self._consume_comma(val, merged_list, is_last_consumed_a_value)
    else:
        if val.startswith(('{', '[')):
            val = self._consume_object_or_array(val, merged_list)
        else:
            try:
                val = self._consume_string_or_number(val, merged_list, merge_type)
            except ValueError:
                if merge_type is inferred_type:
                    raise
                merge_type = inferred_type          # declared-type → inferred-type fallback ladder
                val = self._consume_string_or_number(val, merged_list, merge_type)
...
if merge_type is str:
    return merged_list[0]                           # str fields keep only the FIRST occurrence
elif merge_type is list:
    return self._merged_list_to_str(merged_list, field_name)
else:
    for item in merged_list:
        merged_dict.update(json.loads(item))        # dict fields update-merge across ALL occurrences
    return json.dumps(merged_dict)
```

**Flow:** `_resolve_parsed_args` walks every parsed dest: list values are either comma-joined verbatim for
`is_no_decode` fields or pushed through `_merge_parsed_list`; `:subcommand` keys collect selected
subcommand dests; kebab-case enum inputs are snake-normalized only when they match an enum member.
Merge type comes from `_cli_dict_args` (dict/Mapping annotations recorded at argument-registration time),
else `list`; union-of-dict annotations get an *inferred* type — `list` when the flag repeats or the first
value starts with `[`, else `str`. The tokenizer strips surrounding brackets, keeps quoted commas intact,
and any failure re-raises as `SettingsError(f'Parsing error encountered for {field_name}: {e}')`.
`_merged_list_to_str` then enforces Decode/NoDecode consistency across AliasPath indices (mixing →
SettingsError) and decides numeric quoting by probing `TypeAdapter(annotation).validate_python(['1'])` —
if `'1'` survives as `str`, bare numbers must be re-quoted to stay strings in the joined `[...]`.
**Invariant:** Order-preserving across occurrences and separators; `str` = first-wins, `list` =
concatenate-and-reserialize, `dict` = later keys override earlier. Everything re-enters normal validation
as a string, so type errors surface from pydantic, not the tokenizer.
**Probe:** `python3 -m pytest tests/test_source_cli.py -k "test_cli_list_arg or test_cli_list_json_value_parsing" -p no:cacheprovider -q` — EXECUTED PASSING (3 passed); tests/test_source_cli.py:1136-1148 folds `["1","2"]`, `"3","4"`, `"5"`, `"6"` into `[1,2,3,4,5,6]`; 1288-1298 mixes `true,"true",null,"null"` keeping JSON vs string distinction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "merge parsed list consume string number append action", limit: 10 });
```

## Verdict
Adopt the three-outcome fold (first-token / bracket-reserialize / dict-update-merge) with the
declared→inferred type fallback and the probe-based quoting decision. Adapt the wire format (JSON-ish
strings) to whatever your downstream decoder accepts; omit kebab-case enum normalization without
kebab_case='all'.
