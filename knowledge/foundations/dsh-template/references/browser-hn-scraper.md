<!-- capsule-v2 -->
# Browser HN scraper — scrape Hacker News front-page submissions with cheerio

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a Node script scrape Hacker News front-page submissions (title, url, points, author, time, comments) with cheerio, as both a reusable exported function and a CLI?

## Cheerio HN scraper
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-hn-scraper.js` (whole file, 98 lines); `scrapeHackerNews` (18–75), the CLI guard (78–96).
**Signature:** `async function scrapeHackerNews(limit = 30): Promise<Array>`; exported at the bottom. CLI: `node browser-hn-scraper.js [--limit <number>]` → prints JSON + a stderr summary. Uses `cheerio` only (no browser).
**Data Shape:** each submission is `{ id, title, url, points, author, time, comments, hnUrl }`. `limit` caps the returned array (default 30). `hnUrl = https://news.ycombinator.com/item?id=${id}`.

### Decisive source
```js
async function scrapeHackerNews(limit = 30) {
  const url = 'https://news.ycombinator.com';
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  const html = await response.text();
  const $ = cheerio.load(html);
  const submissions = [];
  // Each submission has class 'athing'; the metadata row is the NEXT sibling.
  $('.athing').each((index, element) => {
    if (submissions.length >= limit) return false; // Stop when limit reached
    const $element = $(element);
    const id = $element.attr('id');
    const $titleLine = $element.find('.titleline > a').first();
    const title = $titleLine.text().trim();
    const url = $titleLine.attr('href');
    const $metadataRow = $element.next();
    const $subtext = $metadataRow.find('.subtext');
    const $score = $subtext.find(`#score_${id}`);
    const pointsText = $score.text();
    const points = pointsText ? parseInt(pointsText.match(/\d+/)?.[0] || '0') : 0;
    const author = $subtext.find('.hnuser').text().trim();
    const time = $subtext.find('.age').attr('title') || $subtext.find('.age').text().trim();
    const $commentsLink = $subtext.find('a').last();
    const commentsText = $commentsLink.text();
    let commentsCount = 0;
    if (commentsText.includes('comment')) {
      const match = commentsText.match(/(\d+)/);
      commentsCount = match ? parseInt(match[0]) : 0;
    }
    submissions.push({ id, title, url, points, author, time, comments: commentsCount, hnUrl: `https://news.ycombinator.com/item?id=${id}` });
  });
  return submissions;
}
// CLI guard
if (import.meta.url === `file://${process.argv[1]}`) { /* parse --limit, call, print JSON */ }
export { scrapeHackerNews };
```

**Flow:** (1) `fetch` the HN front page, throw on non-OK; (2) `cheerio.load`; (3) iterate `.athing` rows, stopping at `limit`; (4) pull the title/url from `.titleline > a`; (5) read the next sibling's `.subtext` for points (`#score_<id>`), author (`.hnuser`), time (`.age`), and comments (the last `a`, only if it contains "comment"); (6) push a normalized submission object; (7) CLI prints JSON + a stderr count.

**Invariant:** the metadata row is the next sibling of `.athing` (not a child); points/comments are parsed defensively (default 0); the loop stops exactly at `limit`; the function is both importable and CLI-runnable via the `import.meta.url` guard.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`; `scrapeHackerNews` resolves in the graph at `browser-hn-scraper.js:18-75`). The `.athing`/next-sibling parsing is the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "scrapeHackerNews athing subtext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the cheerio `.athing` + next-sibling `.subtext` parse, the defensive points/comments extraction, the `limit` cap, and the importable+CLI dual surface. Adapt the target URL/selectors to other sites. Omit if a browser-rendered scrape is needed (this uses plain fetch).
