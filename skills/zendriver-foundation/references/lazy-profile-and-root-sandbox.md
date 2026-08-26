<!-- capsule-v2 -->
# lazy-profile-and-root-sandbox — deferred temp profiles and the root→no-sandbox auto-correct

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** When is the temp profile created, and why does sandbox silently turn off under root?

## user_data_dir is a lazily-materialized property
**Path/Symbol:** `zendriver/core/config.py:Config.user_data_dir` (:143-168), `uses_custom_data_dir` (:166-168), `temp_profile_dir` (:282-285), root auto-correct (:104-108); consumed by `Browser._cleanup_temporary_profile` (`browser.py:650-669`).
**Signature:** `@property def user_data_dir(self) -> str` (creates `mkdtemp(prefix="uc_")` on first read when unset).
**Data Shape:** `_user_data_dir: str | None` + `_custom_data_dir: bool`; setter marks custom on truthy path, resets both on falsy.

### Decisive source
```python
# defer creating a temp user data dir until the browser requests it so
# config can be used/reused as a template for multiple browser instances
self._user_data_dir: str | None = None
self._custom_data_dir = False
...
if is_posix and is_root() and sandbox:
    logger.info("detected root usage, auto disabling sandbox mode")
    self.sandbox = False
```

**Flow:** Config construction records but does not create anything; the first `.user_data_dir` *read* (during argv build in `__call__`) materializes one temp dir. Cleanup at browser stop only removes the dir when `not uses_custom_data_dir`, retrying `shutil.rmtree` up to 5 attempts with 0.15s sleeps for Windows-style file locks (:654-670). Root detection flips sandbox off at config time because Chrome refuses its sandbox under uid 0.
**Invariant:** a shared Config must yield *distinct* profile dirs per browser — hence lazy creation per instance copy (`Browser.__init__` deep-copies the config, so each instance's first read makes its own dir). A port that creates the temp dir in the constructor pins every cloned instance to the same profile.
**Probe:** direct test coverage via cookie save/load round-trip which relies on profile lifecycle: `tests/core/test_browser.py::test_cookies_save_and_load_round_trip`; static anchor: `grep -n 'def is_root' zendriver/core/config.py` → :269.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "temp_profile_dir user_data_dir lazy", limit: 5 });
```

## Verdict
Adopt lazy per-instance profile materialization and the cleanup-vs-custom guard; adapt the root auto-correct to your platform's privilege model; omit the `uc_` prefix convention if you namespace by app.
