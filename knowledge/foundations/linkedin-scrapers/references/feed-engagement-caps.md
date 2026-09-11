<!-- capsule-v2 -->
# Feed engagement caps — how do I auto-like and comment on the feed without tripping spam detection?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what volume limits, gating rules, and content strategy keep automated feed engagement below LinkedIn's bot thresholds?

## LinkedinEngagementService.process — slice(0,4) likes, >30-likes gate for comments, shuffled comment pool
**Path/Symbol:** `lib/linkedin/linkedin.engagement.service.ts:LinkedinEngagementService.process` (:14–130).
**Signature:** `async process(page: Page, cdp: CDPSession, data: any) -> void`.
**Data Shape:** candidate posts collected in-page from `[type="like-icon"], [type="thumbs-up-outline"]` icons whose closest `button:not(.react-button--active)` has an id; each row `{like: buttonId, comment: buttonId|null, id: postId, totalLikes: number}` where `totalLikes = +(countText.match(/\d/g)?.join('') || 0)` (handles "1,234" thousands separators by digit-concat).

### Decisive source
```ts
// COLLECTION CAP — hard limit 4 posts per run, decided IN-PAGE before any click
.filter((f) => f.id)
.slice(0, 4);

for (const id of ids) {
  try {
    await this.moveMouseAndScroll(page, `#${id.like}`, undefined, false, -700);
    await timer(1000);
    await this.moveAndClick(page, `#${id.like}`);
    await timer(1000);

    // COMMENT GATE — only high-traction posts earn a comment (bigger signal,
    // smaller relative footprint; low-like posts get likes only)
    if (id.totalLikes > 30) {
      await this.moveMouseAndScroll(page, `#${id.comment}`, undefined, false, -700);
      await timer(1000);
      await this.moveAndClick(page, `#${id.comment}`);
      await timer(1000);
      // CONTENT POOL — shuffle(generic phrases)[0], typed at human delay 20ms
      await page.keyboard.type(shuffle([
        "Thank you for sharing", "Great Share", "Cool",
        "Thanks for posting 💯🔥", "💯💯", "Great content keep it up 👌🏼",
        "Great 👍", "Awesome!!",
      ])[0], { delay: 20 });
      await timer(1000);
      await this.moveAndClick(page, ".comments-comment-box__submit-button");
    }
  } catch (err) {}   // per-post failure isolation: one broken post never kills the run
}
```
The pre-wait `waitForFunction` re-collects like-icon ids until at least one inactive button exists (initial wheel deltaY 1500 + 4000ms settle first); `.react-button--active` exclusion means already-liked posts are skipped at collection time, not click time.
**Flow:** feed → scroll+settle → collect inactive like buttons → cap 4 → per post: scroll-to(-700) → like → IF >30 likes: open comments → type shuffled generic phrase → submit; every post isolated in its own try/catch.
**Invariant:** volume is capped BEFORE clicking (collection-time slice), not by a loop counter after — the page never sees more than 4 engagement events per pass; already-active buttons are excluded so re-runs are naturally idempotent; comments (the higher-risk action) are gated on social proof (>30 likes) rather than fired at the same rate as likes.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchor `LinkedinEngagementService.process` resolves :14–130 exactly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "engagement like-icon thumbs-up-outline totalLikes comment", limit: 5 });
```

## Verdict
Adopt collection-time caps + traction-gated comments + shuffled generic-content pool as the minimal-viable-feed-warmup pattern (complements throttle-classification-ladder's reactive layer with proactive restraint); adapt the 4-post/30-like constants to account age and risk appetite, refresh the phrase pool (they date visibly); omit emoji-heavy phrasings for professional verticals. Contrast: inbox-harvest-shuffle randomizes ORDER of reads; this caps VOLUME and gates WRITES — reads and writes need different evasion because only writes create observable side effects.
