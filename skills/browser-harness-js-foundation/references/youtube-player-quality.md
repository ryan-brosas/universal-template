<!-- capsule-v2 -->
# YouTube Player Quality Contract — labels, forced quality vs SABR reality

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does ytdl select and verify video quality through the page's own player API?

## Path / Symbol
`skills/ytdl/scripts/ytdl` :104-117 (`-q` → label map), :262-273 (force + play), :429-435 (actual-quality readback), metadata read :168-176.

## Signature
```js
// -q maps to YouTube player quality LABELS (not resolutions):
360p→medium, 480p→large, 720p→hd720, 1080p→hd1080, 1440p→hd1440, 2160p|4k→hd2160,
best|max→"max", audio→"tiny" (+ keep="audio")
// Force (best-effort — "SABR may ignore it"):
if (p.setPlaybackQualityRange) p.setPlaybackQualityRange(YTQ, YTQ);
if (p.setPlaybackQuality)     p.setPlaybackQuality(YTQ);
// Read available levels for --info and validation:
const qualities = p.getAvailableQualityLevels ? p.getAvailableQualityLevels() : [];
// Read what ACTUALLY played (post-capture):
const actual = p.getPlaybackQuality ? p.getPlaybackQuality() : '';
```

## Data Shape
Result carries BOTH `forcedQuality` and `actualQuality` so callers can detect when SABR served less than requested; `#movie_player` is the stable player element id all calls key on (paired `<video>` for media state).

## Decisive source
Play nudge comment :254-261: "Force the requested quality (best-effort — **SABR may ignore it**) and play muted at 16x so the player fetches+appends every segment fast. The model is just 'view it, sped up'; capture happens in the MSE hook as it plays." Every `try{...}catch(e){}` around player-API calls because these are undocumented internals that vary by player build. Shorts handling (:88-101): `youtube.com/shorts/<id>` normalizes to `watch?v=<id>` because "a Short is just a video... the Shorts page is a different UI shell around the same #movie_player; the watch URL is the path ytdl's selectors / autonav / quality logic targets." ID grammar: bare `[A-Za-z0-9_-]{11}`, else `?v=`, `youtu.be/`, `/embed/`, `/shorts/` sed ladders.

## Flow / Invariant
1. Request quality through the player API, never trust it — read back `getPlaybackQuality` after capture.
2. Wrap every undocumented player call in try/catch; degrade to default quality, not failure.
3. Normalize any URL shape to `watch?v=` before driving selectors.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "setPlaybackQualityRange" skills/ytdl/scripts/ytdl` → 1; `grep -c "getAvailableQualityLevels" skills/ytdl/scripts/ytdl` → 2; `grep -c "shorts" skills/ytdl/scripts/ytdl` → ≥3. Live quality behavior needs a real logged-in YouTube session (sandbox-blocked) — coverage caveat recorded.

## Retrieve
grep-first (`setPlaybackQualityRange`, `movie_player`, `hd2160`).

## Verdict
ADOPT the label table + force-then-verify pattern for any YouTube automation touching quality.
