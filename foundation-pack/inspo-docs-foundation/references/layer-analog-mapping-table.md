<!-- capsule-v2 -->
# Layer→analog mapping table — how does a two-column table bind a closed product's layers to open-source analogs?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** How do you map each layer of an opaque (compiled/closed) reference product onto concrete OSS study targets so coverage gaps stay visible?

## Two-column analog table
**Path/Symbol:** `README.md:37-46` (`## How they map to the LinkedHelper stack`); header row 38 `| LH layer (compiled .jsc) | OSS analog in this batch |`, seven mapping rows lines 40-46.
**Signature:** `| <proprietary layer name> | <OSS repo(s) from the batch> |` — left column names the closed artifact including its file format (`compiled .jsc`), right column names one or more batch repos.
**Data Shape:** multi-cover rows list several analogs separated by commas (`SelectorsManager / DOM actions | linkedin-profile-scraper-api, LinkedIn-Easy-Apply-Bot`); rows may pair unlike kinds when they cover the same layer (`front + SaaS backend | growchief (monorepo), locoagent (AI)`).

### Decisive source
```markdown
| LH layer (compiled .jsc) | OSS analog in this batch |
|---|---|
| InstanceManager / multi-account | undetectable-fingerprint-browser |
| ProxyManager / throttling | JobSpy (proxy support), linvo-scraper |
| SelectorsManager / DOM actions | linkedin-profile-scraper-api, LinkedIn-Easy-Apply-Bot |
| API approach (voyager) | linkedin-private-api |
```
(`docs/README.md:38-43`)

**Flow:** enumerate the closed product's internal layers by name → for each, point at the batch repo(s) whose code teaches that layer → leave layers with no analog as explicit empty/absent rows rather than inventing weak matches.
**Invariant:** every right-column entry is a repo that exists in this same index (no dangling references); the left column preserves the proprietary naming verbatim so future reverse-engineering work stays aligned. Verified live: `grep -c '^|' docs/README.md` = 9 (header + separator + 7 rows).
**Probe:** deterministic probe: `grep -c 'InstanceManager' docs/README.md` = 1 AND `grep -c '^|' docs/README.md` = 9.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "How they map", limit: 5 });
// resolves docs.README.How-they-map-to-the-LinkedHelper-stack @ README.md:37 (EXECUTED 2026-08-24: 1 result;
// search_graph query/name_pattern forms return 0 on this doc-shaped graph — Section nodes are tokenless/filtered)
```

## Verdict
Adopt the two-column layer-mapping table for any closed-product study program; adapt layer names to your target's architecture; omit scoring or maturity columns — presence of an analog per layer is the information the table must keep honest.
