<!-- capsule-v2 -->
# BrowserProfile config diamond — how do five Playwright kwarg surfaces merge into one validated model without losing fields?

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When porting the profile/config layer, which MRO order and validator placement keep all Playwright launch/connect/context kwargs valid while adding browser-use-only fields?

## Four-parent MRO diamond with field-alias shadowing
**Path/Symbol:** `browser_use/browser/profile.py:BrowserProfile` (574-736), parents `BrowserConnectArgs` (381), `BrowserLaunchPersistentContextArgs` (534), `BrowserLaunchArgs` (395), `BrowserNewContextArgs` (500).
**Signature:** `class BrowserProfile(BrowserConnectArgs, BrowserLaunchPersistentContextArgs, BrowserLaunchArgs, BrowserNewContextArgs)`
**Data Shape:** Pydantic BaseModel, `extra='ignore'`, `validate_assignment=True`, `revalidate_instances='always'`, alias choices let old API names (`save_har_path`/`save_recording_path`/`trace_path`/`downloads_dir`) populate new fields. Fields NOT set explicitly do not run validators (`validate_default` unset) — e.g. `user_data_dir=None` survives construction; only an explicit value passes `validate_user_data_dir`.

### Decisive source
```python
class BrowserProfile(BrowserConnectArgs, BrowserLaunchPersistentContextArgs, BrowserLaunchArgs, BrowserNewContextArgs):
    """A BrowserProfile is a static template collection of kwargs that can be passed to:
        - BrowserType.launch(**BrowserLaunchArgs) ... - BrowserSession(**BrowserProfile)
    """
    record_video_dir: Path | None = Field(
        default=None,
        description='Directory to save video recordings. ...',
        validation_alias=AliasChoices('save_recording_path', 'record_video_dir'),
    )
    # these shadow the old playwright args on BrowserContextArgs, but it's ok
    # because we handle them ourselves in a watchdog and we no longer use playwright
```

**Flow:** user dict → per-surface parent models define the Playwright contract (context args, connect args, launch args, persistent-context args) → `BrowserProfile` diamond merges them, re-declares recording fields with alias choices, adds browser-use-only knobs (`disable_security`, `allowed_domains`, `keep_alive`, wait timings, iframe caps) → `model_post_init` runs `detect_display_configuration()` then `_copy_profile()` → consumers slice the profile back per Playwright call.
**Invariant:** MRO order is load-bearing for the diamond; re-declared fields with `validation_alias=AliasChoices(...)` must keep BOTH names or old callers silently lose config (extra='ignore' drops unknowns without error). Porters who flatten to one flat model break old-name compat and per-call slicing.
**Probe:** `tests/ci/test_chrome_profile_helpers.py` pins sibling chrome.py helpers; profile construction itself is covered by deterministic probe: construct `BrowserProfile(headless=True)` → `user_data_dir is None` (validators don't run on defaults).
**Coverage caveat:** no dedicated upstream suite for the diamond; verified by direct execution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "BrowserProfile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-parent diamond + AliasChoices pattern as the portable shape for "config that fans out to several library call signatures"; adapt field sets to your Playwright version; omit cloud/demo/captcha product knobs. State the validate_default caveat whenever relying on post-construction None checks.
