<!-- capsule-v2 -->
# CLI app discovery — how does `flask` find the app, and which errors are distinguished from import failures?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the discovery ladder and the wrong-args factory detection trick?

## ScriptInfo.load_app / find_best_app / _called_with_wrong_args
**Path/Symbol:** `src/flask/cli.py:find_best_app` (41–91), `.find_app_by_string` (120–197), `.prepare_import` (200–226), `.locate_app` (241–264), `ScriptInfo.load_app` (333–372), `._called_with_wrong_args` (94–117), `.with_appcontext` (380–402), `FlaskGroup.make_context/parse_args` (657–688).
**Signature:** `load_app() -> Flask` memoized in `_loaded_app`; `prepare_import(path) -> module_name` walks up past `__init__.py`s inserting sys.path[0].
**Data Shape:** discovery order: explicit `-A/--app`/FLASK_APP (`module:name`, name may be `factory(args)` with literal-eval'd args) → `wsgi.py` → `app.py`; inside a module: attrs `app`, `application` → sole Flask instance → factories `create_app`, `make_app`.

### Decisive source
```python
def _called_with_wrong_args(f):
    tb = sys.exc_info()[2]
    try:
        while tb is not None:
            if tb.tb_frame.f_code is f.__code__:
                return False        # error raised INSIDE the factory
            tb = tb.tb_next
        return True                 # TypeError came from the call itself
    finally:
        del tb                      # break reference cycle
```
`FlaskGroup.make_context` sets `os.environ["FLASK_RUN_FROM_CLI"] = "true"` so a stray top-level `app.run()` becomes a no-op; `--debug` callback writes `FLASK_DEBUG=1/0` EARLY via env var so factories read it; `get_command/list_commands` load app commands lazily and degrade to an error line if the app fails to import.

**Flow:** parse eager env-file/app options → ScriptInfo memoized load → module locate (ImportError with tb_next ⇒ failure INSIDE user module: full traceback; bare "not found" ⇒ NoAppException) → best-app ladder → debug flag applied through the descriptor.
**Invariant:** a factory raising its own exception must surface that exception, not NoAppException — hence frame-code walking instead of except-TypeError; plugin commands come from entry_points group "flask.commands" once.
**Probe:** `grep -Fc 'tb.tb_frame.f_code is f.__code__' src/flask/cli.py` = 1; `grep -Fc 'tb_next:' src/flask/cli.py` = 1; `grep -Fc '("app", "application")' src/flask/cli.py` = 1; tests `tests/test_cli.py::test_find_best_app` (:47), `::test_locate_app_raises` (:216), `tests/test_cli.py::test_scriptinfo` (:246).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "ScriptInfo find_best_app locate_app factory", limit: 8 });
```

## Verdict
Adopt the ladder + traceback discrimination + FLASK_RUN_FROM_CLI no-op. Adapt option names. Omit dotenv plumbing (host-specific).
