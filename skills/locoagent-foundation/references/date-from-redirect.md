<!-- capsule-v2 -->
# Date-from-redirect — how do you key an output dir and data file by the site's actual date instead of the local clock?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a URL redirects to a dated page, why must the date come from the redirect target, and how is it threaded into output paths and the saved data?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/hf-daily-papers.ts`: date extraction (`:139-148`), output-dir derivation (`:148`), data-file date (`:247-250`).
**Signature:** `const dateMatch = currentUrl.match(/\/papers\/date\/(\d{4}-\d{2}-\d{2})/)`; `const hfDate = dateMatch ? dateMatch[1]! : new Date().toISOString().split('T')[0]!`.
**Data Shape:** `OUTPUT_DIR = resolve(ROOT, 'workflows', config.outputDir ?? '.tmp', 'hf-' + hfDate)`; saved `papers.json` carries `{ date: hfDate, source: 'https://huggingface.co/papers/date/' + hfDate, fetchedAt, totalPapers, papers }`.

### Decisive source
```ts
ab('open https://huggingface.co/papers')   // redirects to today's dated page
ab('wait 2000')
const currentUrl = ab('get url')
// Extract actual date from redirect URL: /papers/date/YYYY-MM-DD
const dateMatch = currentUrl.match(/\/papers\/date\/(\d{4}-\d{2}-\d{2})/)
const hfDate = dateMatch ? dateMatch[1]! : new Date().toISOString().split('T')[0]!
// OUTPUT_DIR is set AFTER we detect the actual HF date from redirect URL
OUTPUT_DIR = resolve(ROOT, 'workflows', config.outputDir ?? '.tmp', `hf-${hfDate}`)
```

**Flow:** open the undated `/papers` entry → wait for the redirect → read the final URL → regex-capture the `YYYY-MM-DD` from `/papers/date/...` → fall back to the local ISO date only if the regex misses → derive the output directory from THAT date → later write `papers.json` whose `date` and `source` both reference the captured date.
**Invariant:** The directory and data-file date are keyed by the SITE's date from the redirect URL, NOT the local system clock — the site may publish a different day than the machine's timezone, and a mismatch would scatter a single day's run across two dirs or mislabel the data. The local clock is only a fallback when the redirect can't be parsed. OUTPUT_DIR is computed lazily (after the redirect is known), not at module scope.
**Probe:** No direct test for this executor (coverage caveat — source-grounded; file is `parse_partial` at :110 only, outside every cited symbol). Deterministic probes: grep pins the regex at `:143`, the fallback at `:144`, and `OUTPUT_DIR = resolve(... hf-${hfDate})` at `:148`; `search_graph --name-pattern "outputResult"` resolves this file's `outputResult`; `check_index_coverage` stdin-JSON reports `partial` at :110 only (outside cited ranges).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "hfDate redirect papers date OUTPUT_DIR", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt redirect-target date capture with local-clock fallback for any workflow whose output is keyed to a site-published date. Adapt the URL shape and regex. Omit nothing — keying by the local clock is the exact bug this layout prevents.
