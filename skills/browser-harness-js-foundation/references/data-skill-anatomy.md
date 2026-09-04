<!-- capsule-v2 -->
# Data-Skill Anatomy — one bash CLI = one quoted-heredoc REPL snippet

## Source
Repo: browser-harness-js @ main`6b1894061e7a09a65a974d7d65a210b9a7ef06e0` (base_sha unchanged; graph ready, full mode, 3,372n/6,203e, parse_partial 0).

## Question
How are the eight data skills (findata/gmaps/gnews/gsearch/rsearch/ttdl/xsearch/ytdl) structured so a porter reproduces the architecture rather than any single site hack?

## Path / Symbol
`skills/{findata,gmaps,gnews,gsearch,rsearch,ttdl,xsearch,ytdl}/scripts/<name>` (~2,900 LOC total, bash). Shared skeleton present in every script.

## Signature
```bash
command -v browser-harness-js || <self-heal symlink from ../cdp/sdk/browser-harness-js into ~/.local/bin>
<arg validation BEFORE spawning the browser>          # counts must be numeric — they flow into JS literals
raw=$(browser-harness-js <<EOF ... EOF)               # snippet evaluated by the persistent REPL daemon
case "$raw" in *'"ok":true'*) ;; *) echo fail >&2; exit 1;; esac   # ttdl/ytdl defensive result check
```

## Data Shape
Snippet returns a JSON string or pretty text; the bash side parses with `grep -oE` + `sed -n 's/...'` only — **no jq dependency** (documented design constraint; BSD-incompatible sed alternation also avoided).

## Decisive source (whole-file reads this pass)
- Self-heal block identical in all 8 scripts (ytdl :29-38, gmaps :33-42, gsearch :8-17, xsearch :8-17, gnews :28-37, rsearch :30-39, findata :11-20, ttdl :44-53): resolves `$(dirname $0)/../cdp/sdk/browser-harness-js`, symlinks into `~/.local/bin`, exports PATH — so the skill works straight from a fresh clone without running `setup`.
- Validation-before-spawn examples: gnews :66-69 rejects non-numeric count *before* the browser launches ("it flows into a JS numeric literal"); gmaps :117-135 validates count 1..30, route ≥2 ≤25 places, optimize ≥2 ≤12 places, mode whitelist; rsearch :96-118 sort/time whitelists + subreddit charset `[A-Za-z0-9_]*`; findata :92-121 period whitelist, numeric limit, date-pair coherence (`P1 >= P2` rejected via node Date.parse).
- Per-call tab discipline everywhere: `Target.createTarget({url:"about:blank", background:true})` → `Target.attachToTarget({flatten:true})` → per-call `sessionId` → work → `finally { session.closeTab(...).catch(()=>{}) }`. Fire-and-forget close means errors never leak tabs; parallel invocations are safe because nothing touches `activeSessionId` (the clobbering hazard the SDK's `use()` would create). EXCEPTION: ytdl/ttdl create **foreground** tabs (see mse-appendbuffer-hook).
- Stats channel: ytdl/ttdl `_stats[]` + `vlog()` collected in-page and returned inside the JSON (`"_stats":[...]`) because "the REPL daemon's stderr isn't wired to this CLI" — extracted by `grep -oE '"_stats":\[[^]]*\]'` when `-v`.

## Flow / Invariant
1. Validate everything cheaply first; never spend a tab launch on a bad arg.
2. One tab per call, closed in `finally`, fire-and-forget — crash safety AND parallelism come from the same idiom.
3. Results cross the bash↔JS boundary ONLY as the snippet's return value; keep flat fields quote-free if you plan to grep them out (ytdl comment: "These fields carry no escaped quotes, so grep+sed is safe").
4. The REPL daemon persists across calls (port 9876) but each call reconnects defensively: `if (!session.isConnected()) try { await session.connect() }`.

## Probe (direct tests)
Real runner available. SDK suites executed at this pin: `node --experimental-strip-types --test session.test.ts axview.test.ts video.test.ts` in a scratch copy with dev deps installed → **1+11+5 = 17 passed, 0 failed**. Each data skill ships its own smoke harness: `bash skills/<skill>/scripts/test` exits **77 when no debuggable browser** (skip-not-fail contract), asserts placeholders (`__GMAPS_`) never leak into output, and checks deterministic guards without a page (gmaps test "-- guards --" section).

## Retrieve
`codebase-memory-mcp cli search_graph --project browser-harness-js --query "closeTab"` → resolves `session.closeTab` (session.ts:243); entry points list shows the SDK surface the snippets ride on.

## Verdict
ADOPT whole: the validate-first / one-tab-per-call / return-value-only / self-healing-PATH skeleton is the reusable port; the per-site extraction logic lives in the sibling capsules.
