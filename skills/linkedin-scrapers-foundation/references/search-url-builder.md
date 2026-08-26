<!-- capsule-v2 -->
# Search-URL builder — how do I encode LinkedIn search filters into query strings instead of clicking filter UIs?

**Source:** EasyApplyJobsBot CC-BY-NC `main@70fe7484` (`utils.LinkedinUrlGenerate` :166–330); contrast open-linkedin-api MIT `search_people` filter-string assembly (:379–429); contrast LinkedIn-Easy-Apply-Bot Apache-2.0 `next_jobs_page` (:679–690). Codebase Memory `EasyApplyJobsBot`. **Question:** what are the canonical parameter encodings (f_E, f_WT, f_TPR, f_JT, geoId, f_AL) and the multi-value `%2C` convention?

## LinkedinUrlGenerate
**Path/Symbol:** `utils.py:LinkedinUrlGenerate.generateUrlLinks` (:167–173) with per-facet builders `jobExp` (:193–225), `datePosted` (:227–238), `jobType` (:240–276), `remote` (:278–298), `salary` (:300–321), `sortBy` (:323–330), `checkJobLocation` (:175–191).
**Signature:** cross-product `for location in config.location: for keyword in config.keywords:` → one URL per (keyword, location) pair; first facet value renders bare (`&f_E=3`), subsequent values append URL-encoded commas (`%2C4`).
**Data Shape:** base `constants.linkJobUrl + "?f_AL=true&keywords=" + …`; facet map: experience Internship…Executive → `f_E=1..6`; workplace On-site/Remote/Hybrid → `f_WT=1..3`; date 24h/week/month → `f_TPR=r86400|r604800|r2592000`; job type F/P/C/T/V/I/O → `f_JT=`; salary tiers $40k..$200k → `f_SB2=1..9`; continent names → hard-coded `geoId`s (asia=102393603, europe=100506914, northamerica=102221843…).

### Decisive source
```python
url = constants.linkJobUrl + "?f_AL=true&keywords=" + keyword \
      + self.jobType() + self.remote() + self.checkJobLocation(location) \
      + self.jobExp() + self.datePosted() + self.salary() + self.sortBy()
...
case "Mid-Senior level": jobExp = "&f_E=4"        # FIRST selection
for index in range(1, len(jobtExpArray)):
    case "Director": jobExp += "%2C5"             # SUBSEQUENT selections join with %2C
```

**Flow:** config lists → cartesian product over keywords×locations → per facet translate human labels to LinkedIn's numeric/param codes → first value anchors the param, rest join via `%2C` → emit ready-to-GET URLs (the bot then just iterates `driver.get(url)`).
**Invariant:** `f_AL=true` (Easy Apply only) is anchored in the base so every generated URL honors the apply-mode constraint; multi-select encoding MUST use `%2C` (a literal comma breaks the filter). open-linkedin-api shows the API-side twin: build a `filters` list of `(key,value:List(...))` strings joined by commas inside `List({})`.
**Probe:** no tests upstream for the URL builders — coverage caveat recorded; graph anchor `EasyApplyJobsBot.utils.LinkedinUrlGenerate`. Adjacent tested seam in the same lane: Auto_job_applier's AI answer snapping (`test_answer_question_select_snaps_to_allowed_option`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "generateUrlLinks", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "search_people", limit: 5 });
```

## Verdict
Adopt label→code tables with first-bare/rest-%2C encoding and URL-over-UI filtering; adapt the code tables as LinkedIn rotates them and your config schema; omit geoId hard-coding (resolve dynamically) and the typo'd "Intership" case. Caveat: source-grounded only; verify facet codes against live LinkedIn before porting.
