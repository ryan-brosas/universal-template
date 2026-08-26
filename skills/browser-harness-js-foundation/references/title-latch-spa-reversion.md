<!-- capsule-v2 -->
# Title-Latch Under SPA Reversion — TikTok caption disappears; latch it early

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How do you name a download after page metadata that the page itself destroys seconds after load?

## Path / Symbol
`skills/ttdl/scripts/ttdl` :140-163 (`isGoodTitle`, `titleState`, `latchTitle`), player-ready poll latching :196-215, early title window :217-231, coverage-loop re-latching :368-374, finalize :435-439.

## Signature
```js
// document.title on a LOGGED-OUT ttdl tab shows the real caption briefly (~1s after
// load) then REVERTS to "Sign up | TikTok" once the SPA swaps to a sign-up state.
// On a logged-in tab the real caption PERSISTS. So we LATCH the first GOOD title we
// see whenever we evaluate the page — during the player-ready poll, the fallback
// window, AND the coverage loop (which runs for the whole capture).
function isGoodTitle(t){
  return !!t && t.endsWith("| TikTok") && t !== "Sign up | TikTok"
      && t !== "Log in | TikTok" && t !== "TikTok - Make Your Day" && t !== "TikTok" && t !== "";
}
const titleState = { good: '', og: '' };   // first-good-wins latch + stable fallback
// fallback: og:title "<creator> on TikTok" → strip the suffix for the creator name
```

## Data Shape
Every poll expression returns `{title, og}` alongside its primary payload so latching is free on each tick; final `title = titleState.good || ogName || ''`; bash-side name chain: title → `${author}_${id}` → `"tiktok"`.

## Decisive source
Comment block :141-146 (quoted above). The early-window loop (:217-231) exists because "the <video> and the real title both arrive ~1s after load and can race... This early window matters most for the logged-out case, where the caption reverts to 'Sign up | TikTok' after ~1s." Author/id come from the FINAL post-redirect URL by pure string ops ("no backslash-regex, so the unquoted heredoc passes it through untouched") — `/@<author>/video/<id>`.

## Flow / Invariant
When a site mutates its own metadata, sample-and-latch on EVERY tick you already run rather than reading once at the end; keep an orthogonal stable fallback (og:title) for the reverted state; whitelist good titles instead of blacklist-bad ones beyond the known shells.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "latchTitle" skills/ttdl/scripts/ttdl` → 5 call sites across three phases; `grep -c "isGoodTitle" skills/ttdl/scripts/ttdl` → 2. Live behavior (logged-out revert) not reproducible in this sandbox (no TikTok egress) — noted as coverage caveat; the mechanism is fully pinned statically.

## Retrieve
grep-first (`titleState`, `og:title`, `latchTitle`).

## Verdict
ADOPT for any SPA whose title/meta is transient; pair with the URL-derived author/id extraction which never depends on page state.
