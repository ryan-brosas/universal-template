<!-- capsule-v2 -->
# Windowless browser target — stealth without headless detection

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you run Chromium without a visible window AND without announcing `HeadlessChrome`, and when must you refuse?

## hidden_target.py — measured platform support only
**Path/Symbol:** `linkedin_mcp_server/hidden_target.py:hidden_target_is_supported()` (:60-95); env flag `PW_CHROMIUM_ATTACH_TO_OTHER`; `HiddenTargetError`.
**Signature:** `hidden_target_is_supported() -> bool` = `sys.platform == "darwin"` ONLY.
**Data Shape:** Chromium prepends bare `Headless` to the product name at runtime — no change of BINARY removes it, only of MODE. A target with no UI window behaves like an ordinary page with nowhere to be drawn; Playwright surfaces such `type:"other"` targets only when `PW_CHROMIUM_ATTACH_TO_OTHER` is set in the DRIVER PROCESS environment (undocumented upstream, byte-identical across patchright 1.60.0–1.61.2).

### Decisive source
```text
Measured constraints:
- No DISPLAY ⇒ launch_persistent_context(headless=False) fails
  TargetClosedError before any code runs (container image).
- Under Xvfb, closing the startup page KILLS Chromium — hidden page dies
  with it; keeping that page open keeps everything working. macOS does not
  quit an app when its last window closes — that is why the mechanism
  works there.
- Windows NOT measured: claiming it without looking "would be the kind of
  guess this file exists to avoid". Everything else falls back to real
  headless and says so.
- Honest cost accounting in the docstring: a window IS on screen ~0.5s per
  start (~250ms before launch_persistent_context returns, ~340ms macOS
  teardown, ~90ms ours). Only --no-startup-window reaches zero and it
  hangs Playwright for its full timeout (microsoft/playwright#42093).
HiddenTargetError raised rather than recovered: falling back to headless
would restore the token the user believes is gone; falling back to a
visible window would put one on their screen unannounced.
Env-flag guard against overlapping launches: os.environ is process-global
while the scoped block awaits — measured, two concurrent starts left the
flag set afterwards in 2 of 5 runs.
```
**Flow:** check support (macOS only) → set attach-env under lock around each launch → create windowless target → poll (≤10s, 20ms interval) for Page surface → on failure STOP, never degrade silently.
**Invariant:** Stealth properties come from mode choice, not binary swaps; platform claims must be measured or refused; anti-detection fallbacks are forbidden where they'd silently undo the user's security expectation.
**Probe:** `tests/test_hidden_target.py` pins support gating and flag hygiene.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "hidden_target ATTACH_TO_OTHER HeadlessChrome", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the measured-support ladder + refuse-don't-degrade for stealth browser automation. Adapt to your Playwright fork. Omit macOS timing constants (machine-specific).
