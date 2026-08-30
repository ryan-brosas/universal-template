<!-- capsule-v2 -->
# App/logger construction — what does create_logger attach and when; how are instance paths found?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What logging setup happens lazily on first `.logger` access, and how is root/instance path resolved from import_name?

## create_logger / has_level_handler / find_package family
**Path/Symbol:** `src/flask/logging.py:create_logger` (58–79), `.has_level_handler` (31–47), `.wsgi_errors_stream` LocalProxy (15–28); `src/flask/helpers.py:get_root_path` (587–641); `src/flask/sansio/scaffold.py:find_package/_find_package_path` (717–800); `sansio/app.py:auto_find_instance_path/make_config` (507–518, 479–493).
**Signature:** `create_logger(app) -> Logger`; `find_package(import_name) -> tuple[prefix|None, path]`.
**Data Shape:** default handler = StreamHandler(wsgi_errors_stream) with format `[%(asctime)s] %(levelname)s in %(module)s: %(message)s`; logger name == app.name.

### Decisive source
```python
logger = logging.getLogger(app.name)
if app.debug and not logger.level:
    logger.setLevel(logging.DEBUG)
if not has_level_handler(logger):        # walk parents while propagate
    logger.addHandler(default_handler)

# instance path: not installed → <package_path>/instance ; installed → prefix/var/<name>-instance
def auto_find_instance_path(self):
    prefix, package_path = find_package(self.import_name)
    if prefix is None:
        return os.path.join(package_path, "instance")
    return os.path.join(prefix, "var", f"{self.name}-instance")
```

**Flow:** first `.logger` access → configure-if-needed; handler check walks the hierarchy so app loggers under a configured root don't double-add. Root path resolution ladder: imported module `__file__` → loader.get_filename → import fallback → cwd; `_find_package_path` distinguishes package/module/namespace (`commonpath` of submodule_search_locations).
**Invariant:** handler detection uses EFFECTIVE level vs handler levels up the chain; DEBUG config read once at creation (later debug flips don't reconfigure — docstring-documented); make_config seeds `defaults["DEBUG"] = get_debug_flag()` from env at CONSTRUCTION.
**Probe:** `grep -Fc 'has_level_handler(logger)' src/flask/logging.py` = 1; `grep -Fc '_sentinel' src/flask/sansio/scaffold.py` ≥ 2 (module sentinel reused by blueprints); tests `tests/test_logging.py` (existing_app_logger/parent gain scenarios), `tests/test_basic.py::test_env_overrides` family for FLASK_DEBUG.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "create_logger has_level_handler find_package instance path", limit: 8 });
```

## Verdict
Adopt lazy one-time logger configuration + effective-level handler probe. Adapt instance-path layout. Omit Windows lib-layout branches if unsupported.
