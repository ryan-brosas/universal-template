<!-- capsule-v2 -->
# config-args-pipeline — how do kwargs, defaults, and forbidden flags compose into the exact chrome argv?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** Which flags does Config always send, which are conditional, and why can't users add certain flags themselves?

## __call__ builds argv; add_argument blocks the managed surface
**Path/Symbol:** `zendriver/core/config.py:Config.__call__` (:198-229), `add_argument` (:231-247), `browser_args` property (:139-141), `_default_browser_args` (:119-137).
**Signature:** `def __call__(self) -> list[str]`; `def add_argument(self, arg: str) -> None`; `@property def browser_args(self) -> List[str]  # sorted(defaults + custom)`.
**Data Shape:** `_default_browser_args`: 16 stealth/stability flags (`--remote-allow-origins=*`, `--no-first-run`, `--disable-blink-features`-adjacent set incl. `--disable-features=IsolateOrigins,DisableLoadExtensionCommandLineSwitch,site-per-process`, ...). Kwargs land as attributes via `self.__dict__.update(kwargs)` — that is how `sandbox=False` from `start()` reaches `Config`.

### Decisive source
```python
def add_argument(self, arg: str) -> None:
    if any(
        x in arg.lower()
        for x in ["headless", "data-dir", "data_dir", "no-sandbox", "no_sandbox", "lang"]
    ):
        raise ValueError('"%s" not allowed. please use one of the attributes of the Config object to set it' % arg)
    self._browser_args.append(arg)
```
and the conditional tail of `__call__` (:211-227): `--headless=new` only when truthy headless; `--user-agent=`; `--no-sandbox` when `not self.sandbox`; `--remote-debugging-host/port` only when host/port set; WebRTC leak-block pair when `disable_webrtc` (default True); `--disable-webgl --disable-webgl2` when `disable_webgl` (default False).

**Flow:** constructor → root-user auto-correct (`is_posix and is_root() and sandbox` ⇒ sandbox=False with a log line :104-108) → `__call__` = copy of defaults + `--user-data-dir=<lazy temp>` + re-asserted `--disable-features=IsolateOrigins,site-per-process` + deduped custom args (skipping ones already present) + conditionals above. Host/port default to None; `Browser.start()` fills them (`127.0.0.1` + `free_port()`), so a Config reused as a template stays port-free until launch.
**Invariant:** user-supplied args can never silently override the managed flags — the guard rejects substring matches case-insensitively (`--HEADLESS` also raises). A porter who replaces the guard with an allowlist changes the security posture (root auto-no-sandbox would be bypassable).
**Probe:** direct tests pin argv composition via `create_browser(browser_args=[...])` plumbing in `tests/conftest.py::CreateBrowser` (:45-79); static anchors at the pin: `DisableLoadExtensionCommandLineSwitch` appears at `config.py:134`; `grep -n 'winner = min(rv, key=lambda x: len(x))' zendriver/core/config.py` → :303.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Config browser_args add_argument", limit: 5 });
```

## Verdict
Adopt the deny-guard + conditional-flag composition wholesale for any Chrome launcher; adapt the default flag list per target browser version (it is a stealth trade-off, not gospel); omit the macOS/Windows candidate tables if you resolve executables another way.
