<!-- capsule-v2 -->
# Chrome launch-arg compiler — how do you merge five flag families without --disable-features silently overwriting?

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When compiling the final chromium CLI arg list from defaults + user args + mode families, how do you prevent later `--disable-features=` flags (e.g. disable_security) from clobbering extension-critical defaults?

## get_args(): extract-merge-dedupe pipeline
**Path/Symbol:** `browser_use/browser/profile.py:BrowserProfile.get_args` (895-973); constants `CHROME_DEFAULT_ARGS` (154), `CHROME_DISABLED_COMPONENTS` (37), `CHROME_DISABLE_SECURITY_ARGS` (133), `CHROME_DOCKER_ARGS` (120), `CHROME_HEADLESS_ARGS` (116).
**Signature:** `def get_args(self) -> list[str]`
**Data Shape:** input = profile state + `ignore_default_args: list[str] | Literal[True]`; output = final deduped CLI arg list. `args_as_dict`/`args_as_list` (482-494) do last-wins dict roundtrip with leading-dash stripping.

### Decisive source
```python
# Special handling for --disable-features to merge values instead of overwriting
# This prevents disable_security=True from breaking extensions by ensuring
# both default features (including extension-related) and security features are preserved
disable_features_values = []
non_disable_features_args = []
for arg in pre_conversion_args:
    if arg.startswith('--disable-features='):
        features = arg.split('=', 1)[1]
        disable_features_values.extend(features.split(','))
    else:
        non_disable_features_args.append(arg)
# Remove duplicates while preserving order ... then re-append ONE merged flag
final_args_list = BrowserLaunchArgs.args_as_list(BrowserLaunchArgs.args_as_dict(non_disable_features_args))
```

**Flow:** default family (minus `ignore_default_args`) → user `self.args` → `--user-data-dir`/`--profile-directory` → conditional families (docker, headless, security, deterministic-rendering, window size/position, extensions, proxy, user-agent) → extract ALL `--disable-features=` values into one order-preserving deduped list → single merged flag appended → whole list passes through args_as_dict/args_as_list for general dedupe.
**Invariant:** exactly ONE `--disable-features=` flag survives, containing BOTH default features (`AcceptCHFrame`, `Translate`, …) AND — when `disable_security=True` — `IsolateOrigins,site-per-process`. Chromium treats repeated flags as last-wins, so naive concatenation would drop ~16 default components and break extensions/site isolation assumptions. `ignore_default_args=['--x']` removes only that default; other defaults stay.
**Probe:** deterministic (no upstream suite): `BrowserProfile(headless=True, disable_security=True, user_data_dir='/tmp/x').get_args()` → one `--disable-features=` whose values include `AcceptCHFrame`, `IsolateOrigins`, `site-per-process`; `ignore_default_args=['--disable-popup-blocking']` drops just that default. Executed green in gate 5.
**Coverage caveat:** no upstream unit file pins this function; probe is a direct-execution check.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "get_args", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the extract-merge-dedupe pattern for ANY chromium-style flag set where multiple features can emit the same multi-value flag; adapt the concrete flag tables (they encode live vendor behavior that changes); omit the commented-out experimental entries.
