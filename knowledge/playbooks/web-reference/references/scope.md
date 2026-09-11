# Scope: bounded crawling and URL hygiene

## What "whole site" means

Same host or a relevant site prefix, covering representative routes rather than the full public surface. Defaults: at most 25 pages, depth at most 3, one crawl at a time. For large sites pick representative routes: homepage, pricing, one product or detail page, one docs or content page, an authentication shell when relevant. Do not capture hundreds of near-identical marketing pages.

## Route selection

- An explicit allowlist wins over discovery when the user names routes.
- Crawl same-host links only, inside the chosen prefix.
- Stop at the page cap, the depth cap, or when new routes stop adding design evidence.

## Exclusions (never crawl)

Logout, delete or deactivate actions, account and profile mutations, checkout and payment steps, search results, infinite calendars, pagination beyond a small sample, filter-combination explosions, tracking URLs, analytics endpoints, mutation API endpoints, bulk downloads, and user-specific private routes.

## URL normalization

Deduplicate before queueing:

- strip tracking parameters (`utm_*`, `fbclid`, `gclid`, `mc_eid`);
- drop fragments when the page is identical;
- collapse trailing slashes;
- collapse sort and filter variants unless they change visual evidence.

## Access rules

- Respect robots.txt and rate limits; pace requests; one crawl at a time.
- Never bypass authentication, defeat anti-bot systems, or evade blocks. This is design prior art, not adversarial scraping.
- Authenticated capture uses the user's authorized session only (`references/capture.md`).
- No credentials, cookies, or session dumps inside the bundle; the validator rejects credential-like material.

## Limits and stop conditions

Track page count, asset bytes, and screenshot count against the budget agreed for the question. When a cap hits, record what was skipped in `coverage_gaps` instead of extending the crawl silently.
