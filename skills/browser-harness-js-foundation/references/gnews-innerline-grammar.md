<!-- capsule-v2 -->
# gnews InnerText Line Grammar — position-based field splitting with a sentinel

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does gnews split a news card's unstructured innerText into source/snippet/time without class names?

## Path / Symbol
`skills/gnews/scripts/gnews` card comment :100-112 + `ex()` extractor :113-127 inside the quoted-heredoc snippet.

## Signature
```js
// Each card's innerText reads:
//   source \n title \n [snippet] \n . \n time
// — the standalone "." line separates the snippet from the trailing relative time and is
// absent on cards with no snippet (source/title/time only).
const ex = (a) => {
  const title = (a.querySelector('div[role=heading]')?.textContent || '').trim();
  let lines = (a.innerText || '').replace(/\u00a0/g, ' ').split('\n')
    .map(s => s.trim()).filter(s => s.length > 0);
  let source = '', rest = lines.slice();
  if (rest[0] && rest[0] !== title) { source = rest[0]; rest = rest.slice(1); } // source optional
  if (rest[0] === title) rest = rest.slice(1);                                   // drop title line
  const dot = rest.indexOf('.');
  if (dot >= 0) { snippet = rest.slice(0, dot).join(' '); time = rest.slice(dot+1).join(' '); }
  else          { time = rest.join(' '); }                                      // no-snippet shape
};
```

## Data Shape
`{title, url, source, snippet, time}`; `url` is "the publisher's DIRECT url (no news.google.com redirect wrapper)" — a property of the tbm=nws tab that distinguishes it from Google News proper.

## Decisive source
Comment block :103-111 (quoted above) documents BOTH shapes: with and without the '.' sentinel. Card selection (:100-101): anchors containing a `div[role=heading]` whose href is off-Google (classless doctrine capsule). JSON-mode subtlety :160-165: return `JSON.stringify(results)` NOT the array — "the REPL renders empty arrays as '' by default, which would give jq/JSON.parse callers a parse error on a 0-result query."

## Flow / Invariant
1. Filter blank lines first, then peel known-prefix lines (source-if-different-from-title, then title), then split on the sentinel.
2. Treat the sentinel as optional; absence means empty snippet, not an error.
3. When returning collections across the REPL boundary, stringify explicitly to keep zero-results valid JSON.

## Probe (direct tests)
Deterministic probes at pin: `grep -n 'role=heading' skills/gnews/scripts/gnews` → 4 lines (:77–78 comments, :86 filter, :88 title read); `grep -n "tbm=nws" skills/gnews/scripts/gnews` → 4 lines (:4, :10 comments, :72 URL, :76 comment) — ERRATUM pass-5 execution audit: shipped as "→ 2 / → 3"; both were miscounts at unchanged pin `main@6b189406` (comment-line contamination + arithmetic slips; counts above re-derived against source). Smoke harness present (`scripts/test`, 92L) for live runs. Live layout verification needs Google egress (blocked in sandbox) — grammar pinned verbatim from source.

## Retrieve
grep-first (`role=heading`, `indexOf(".")`, `tbm=nws`).

## Verdict
ADOPT for any innerText-only card parsing; the optional-sentinel handling is what keeps no-snippet cards from corrupting fields.
