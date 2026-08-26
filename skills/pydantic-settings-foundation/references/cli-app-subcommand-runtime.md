<!-- capsule-v2 -->
# CliApp runtime — how does a model run as an app with subcommands, async commands, and unknown-arg tolerance?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** Beyond parsing flags into settings, how do I execute a model as a CLI application — subcommand dispatch, `cli_cmd` entrypoints, async commands inside running loops, and tolerating unknown args?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/main.py:CliApp` (674-993) — `run` (749-829), `_run_cli_cmd` (702-746), `run_subcommand` (831-889) + `get_subcommand` (`sources/base.py` 49-99).
**Signature:** `CliApp.run(model_cls, cli_args=None, cli_settings_source=None, cli_exit_on_error=None, cli_cmd_method_name='cli_cmd', **model_init_data) -> T`
**Data Shape:** per-instance parser state rides a class-level dict keyed by object identity: `_subcommand_stack[id(model)] = (cli_source, parser, subcommand_dest)`.

### Decisive source
```python
if inspect.iscoroutinefunction(command):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():            # Jupyter-style: own thread, own loop
        exception_container = []
        def run_coro() -> None:
            try:
                asyncio.run(command(model))
            except Exception as e:
                exception_container.append(e)
        thread = threading.Thread(target=run_coro); thread.start(); thread.join()
        if exception_container:
            raise exception_container[0]
    else:
        asyncio.run(command(model))
else:
    command(model)
```
Subcommand resolution (`run_subcommand` → `get_subcommand`, base.py 84-98): scan model fields for
`_CliSubCommand` metadata, return the first non-None; none set ⇒ `SystemExit` (default) or `SettingsError`
per `cli_exit_on_error`. Context-free errors get help text appended:
`if err.__context__ is None and err.__cause__ is None ... error_message = f'{err}\n{...format_help(parser)}'`.
Stack entries are pushed before dispatch and removed in `finally`.

**Flow:** `run` validates the model class (BaseModel/dataclass only), normalizes `cli_args`
(None ⇒ True ⇒ sys.argv[1:] pre-parsed namespace/dict allowed only with an explicit source), then either
drives the BaseSettings pipeline directly or synthesizes a shadow BaseSettings class
(`_get_base_settings_cls`) whose resolved fields feed the original model's constructor. The root stack
entry is pushed, `cli_cmd` runs (optional at root, required in subcommands), stack popped in `finally`.
Unknown-arg tolerance: fields annotated `CliUnknownArgs` collect unparsed tokens during parsing
(parse_known_args); `_load_env_vars` (cli.py 597-611) then *rejects* those unknowns unless the selected
subcommand itself accepts them — `root_parser.error(...)`/`SystemExit(2)` — otherwise merges the buckets
into parsed output.
**Invariant:** Async commands never kill a host event loop (thread isolation); exceptions propagate intact.
Subcommand state is identity-keyed and always cleaned up, so nested `run_subcommand` chains work. A
subcommand that doesn't declare unknown tolerance still fails loudly even when a sibling accepts them.
**Probe:** `python3 -m pytest tests/test_source_cli.py -k "test_cli_app or test_cli_app_async_method_with_existing_loop or test_cli_ignore_unknown_args_subcommand" -p no:cacheprovider -q` — EXECUTED PASSING (3 passed); tests/test_source_cli.py:2450-2463 proves subcommand-B tolerates `--bad` while subcommand-A exits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "CliApp run subcommand cli cmd async loop", limit: 10 });
```

## Verdict
Adopt the identity-keyed runtime stack with finally-cleanup, the optional-root/required-subcommand
entrypoint contract, thread-isolated async dispatch, and per-subcommand unknown-arg scoping. Adapt the
help-enrichment rule to your error channel; omit the shadow-BaseSettings bridge if your host is always a
BaseSettings subclass.
