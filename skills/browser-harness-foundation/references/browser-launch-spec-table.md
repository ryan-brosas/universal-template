<!-- capsule-v2 -->
# Browser discovery + launch spec table — how do you relaunch the RIGHT browser with the RIGHT profile when Chrome is closed?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Given profile dirs from multiple Chromium-family browsers, which app launches and why does last-used-profile matter?

## Profile-fragment launch table + Local State probe
**Path/Symbol:** `src/browser_harness/admin.py:_BROWSER_LAUNCH/_DEFAULT_LAUNCH/_browser_launch_spec/_profile_directory_args/_launch_browser/_chrome_running/_has_local_gui` (:560-568, :811-911).
**Signature:** `_launch_browser() -> bool`; spec rows = `(profile-dir fragment, macOS app name, POSIX commands, Windows start target)` ordered canary→chromium→chrome→edge→brave (+ mac-only Arc/Dia/Comet).
**Data Shape:** BH_CHROME_PATH/CHROME_PATH override wins FIRST (unexecutable path FALLS THROUGH to discovery, never aborts); base dir preference: first toggle-enabled profile else first with Local State; `_profile_directory_args` reads `profile.last_used` from Local State, passing `--profile-directory=` ONLY when that dir exists.

### Decisive source
```python
enabled = remote_debugging_toggle_profiles()
base = enabled[0] if enabled else next((b for b in PROFILES if (b / "Local State").exists()), None)
mac_app, posix_cmds, win_target = _browser_launch_spec(base) if base else _DEFAULT_LAUNCH
profile_args = _profile_directory_args(base)
```

**Flow:** env-path launch → pick base ("Prefers the browser whose profile already has perm box checked") → match LAST TWO path segments against fragments → platform launch (`open -a <app>` with fallback to plain Google Chrome on failure; Windows `start <target>` resolves via App Paths without install-dir knowledge; POSIX shutil.which ladder) → 15s boot-wait lives in ensure_daemon.
**Invariant:** The fragment match is on the PROFILE TAIL not the binary name — profile dir is ground truth for which browser the user consents through; launching without --profile-directory pops Chrome's picker and strands automation; `_chrome_running` name lists include helium (test-pinned); headless-Linux detection gates liveUrl auto-open via DISPLAY/WAYLAND_DISPLAY.
**Probe:** `tests/unit/test_admin.py:153-161` pins helium detection via `ps -A -o comm=`. Launch itself spawns real processes — no direct unit test — coverage caveat; anchors verified at source :827-851 (table+match), :854-865 (last_used probe), :893-903 (per-platform commands).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "launch browser profiles chrome edge brave", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt consent-preferred base selection + fragment-matched launch tables + profile-directory args. Adapt rows to your supported browsers. Omit App Paths trickery where you control install locations.
