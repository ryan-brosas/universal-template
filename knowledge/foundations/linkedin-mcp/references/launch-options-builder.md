<!-- capsule-v2 -->
# Launch-options builder — one pure function so two launch paths cannot drift

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you keep a manual-login browser and an automated-scraping browser IDENTICAL when two call sites build launch options independently?

## build_launch_options / describe_launch
**Path/Symbol:** `linkedin_mcp_server/browser_launch.py` (:1-142, whole module); consumers via trace: `drivers/browser._create_browser_locked`, `_launch_options`, `validate_imported_cookies`, `setup._login_holding_the_profile`, `_login_into_fresh_profile`.
**Signature:** `build_launch_options(browser: BrowserConfig) -> tuple[dict[str, Any], dict[str, int]]`; `describe_launch(launch_options) -> None`.
**Data Shape:** Returns options dict and viewport SEPARATELY (viewport flows through a named BrowserManager arg, not launch options). Pure function of its input — takes the config rather than reading the global.

### Decisive source
````python
# :26-33 — the silent defect this module exists to kill
# Without a channel, Playwright picks the *binary* from `headless` alone:
#   return options2.headless ? "chromium-headless-shell" : "chromium";
# --login forced headless=False and minted every session in the full browser,
# while scraping used the stripped headless shell. One session, two browsers.
launch_options["channel"] = "chromium"

# :63-71 — explicit operator choice wins outright, no channel alongside it
if browser.chrome_path:
    launch_options["executable_path"] = browser.chrome_path

# :100-107 — WebRTC switches only where a proxy exists
if proxy:
    launch_options["proxy"] = proxy
    args.extend(_WEBRTC_STAYS_ON_THE_PROXY)   # both spellings: full Chrome and
                                              # chrome-headless-shell read different ones
````
**Flow:** config in → executable decision (path XOR channel) → container-only WebGL args gated on runtime id ending `-container` (measured 10/10 cold launches per architecture) → proxy + dual-spelling WebRTC containment → args attached if any; viewport returned alongside. Logging is a separate `describe_launch` so a proxy password can never reach a log inside a formatted options dict.
**Invariant:** The binary must not depend on the MODE (`test_the_choice_does_not_depend_on_headless` pins identical options for headless True/False). Capability-changing switches are conditional on the feature they contain (no proxy ⇒ no WebRTC switches). Every non-default switch carries its measured post-mortem inline.
**Probe:** `tests/test_browser_launch.py` (:1-105, whole file): channel naming, path-replaces-channel, mode-independence, viewport passthrough, no-proxy-no-switches, container WebGL set, and combined args ordering all pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "build_launch_options describe_launch channel chromium", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single pure builder + separate credential-free describer for any codebase with more than one browser launch site. Adapt switch sets to your binaries — but keep the measured-evidence comment discipline and the dual-spelling trick when targeting both Chrome and headless-shell. Omit Patchright-specific registry reasoning.
