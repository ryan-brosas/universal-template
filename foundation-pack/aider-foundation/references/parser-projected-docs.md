<!-- capsule-v2 -->
# Parser-projected docs — how do sample config files and README option tables stay permanently in sync with the CLI?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How can .env samples, YAML config references, and markdown option tables be generated so they structurally cannot drift from the live argument parser?

## Three HelpFormatter subclasses re-render every action; default rendering is suppressed
**Path/Symbol:** `aider/args_formatter.py` (whole file, 228 L): `DotEnvFormatter` (:8-78), `YamlHelpFormatter` (:81-172), `MarkdownHelpFormatter` (:175-228); consumed by `aider/args.py`: `get_sample_dotenv` (:898), `get_sample_yaml` (:885), `get_md_help` (:872).
**Signature:** each subclass overrides `_format_usage`, `_format_text`, `_format_action`, `_format_action_invocation`, `_format_args`; the latter two return `""`.
**Data Shape:** rendering reads only argparse action fields: `option_strings`, `metavar`, `default`, `env_var`, `help`, `nargs`, concrete action classes.

### Decisive source
```python
class YamlHelpFormatter(argparse.HelpFormatter):
    ...
    def _format_action(self, action):
        if not action.option_strings:
            return ""
        ...
        for switch in action.option_strings:
            if switch.startswith("--"):
                break
        switch = switch.lstrip("-")
        if isinstance(action, argparse._StoreTrueAction):
            default = False          # flag defaults render as false, not True
        elif isinstance(action, argparse._StoreConstAction):
            default = False
        ...
        if "#" in default:
            parts.append(f'#{switch}: "{default}"\n')   # quote values containing #
```

**Flow:** `get_parser()` is built once; each formatter walks its actions and emits a full artifact: DotEnv renders ONLY options that declare `env_var` (flag≡env is enforced at render time) with commented-out `#ENV=value` lines; Yaml picks the first long switch, expands nargs `*`/`+`/append actions into multi-value examples, quotes `#`-bearing values; Markdown emits `### \`--switch METAVAR\`` blocks with Default / Environment variable / Aliases lines and fences the usage string.
**Invariant:** no option may appear in a shipped sample that does not exist in `get_parser()` — the artifacts are build outputs (`aider --help`-style rendering), never hand-edited files.
**Probe:** deterministic: DSH grep `return ""` on `aider/args_formatter.py` → **13 matches**, including all six suppression points (`_format_usage` ×3 :16/:89, `_format_action_invocation` ×3 :75/:169/:225, `_format_args` ×3 :78/:172/:228). Direct tests: none upstream for the formatters themselves (source-pinned; the artifacts ship via `get_md_help`/`get_sample_yaml`/`get_sample_dotenv` call sites in aider/args.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "YamlHelpFormatter", limit: 10 });
// rank-1: aider.aider.args_formatter.YamlHelpFormatter Class aider/args_formatter.py 81-172 (all 12 methods enumerated)
```

## Verdict
Adopt HelpFormatter-subclass projection whenever a CLI ships config samples or docs tables — it deletes an entire drift class. Adapt section headers, quoting rules, and which fields render to your host's format. Omit aider's specific `#ENV=` commented style if you generate uncommented samples instead.
