<!-- capsule-v2 -->
# Lead ingestion dual lane — how does one "upload leads" call become per-account campaign jobs or search-lead scrapes?

**Source:** growchief AGPL-3.0 `main@abb1e37a6f5595d8d105aef5871a2eeb0c22a1dc`; Codebase Memory `growchief`. **Question:** when a client submits a batch of profile URLs or a search URL, how does the server decide which workflow each account's bot gets, and what contract is advertised back to clients?

## Connected graph-selected seam
**Path/Symbol:** `shared/server/database/workflows/workflows.service.ts` — `WorkflowsService.uploadLeads` (:86–189) and `importURLList` (:191–244); provider metadata source `shared/server/bots/bot.list.ts:botList` (:5); URL normalization `shared/both/utils/url.normalize.ts:URLService.normalizeUrlSafe` (:15–38); downstream consumer `apps/orchestrator/src/workflows/workflow.upload.leads.ts:workflowUploadLeads` (:16–68). Callers: `workflows.controller.ts:44–58`.
**Signature:** `uploadLeads(wid: string, orgId: string, body: UploadLeadsDto /* {link?: string[], searchUrl?: string[]} */): Promise<void | {error}>`; `importURLList(workflowId, organizationId): Promise<{link: {name, identifier, link:{source, flag}}[], searchLink: {name, identifier, searchURL:{description, regex:{source, flag}[]}}[]} | {error}>`.
**Data Shape:** input is a dual-lane payload — `link[]` (profile/company URLs) XOR `searchUrl[]` (search-results pages), decided **per account**. Lane A start options: `{workflowId:'campaign-${wid}-${makeId(20)}', typedSearchAttributes:[organizationId], args:[{workflowId, orgId, body:{urls}}]}`. Lane B: `{workflowId:'url-leads-${wid}-${makeId(20)}', typedSearchAttributes:[workflowId, organizationId, botId], args:[{workflowId, orgId, botId, url}]}`.

### Decisive source
```ts
// :103-119 — lane A: normalize + WWW-convention + platform regex filter
const urlLinks = link?.length ? link.map((url) => {
  const normalized = this._urlService.normalizeUrlSafe(url);
  if (account.platform.isWWW) {
    return normalized.indexOf('//www.') === -1
      ? normalized.replace('://', '://www.') : normalized;
  } else {
    return normalized.replace('://www.', '://');
  }
}) : [];
...
const filterUrls = urlLinks.filter((p) => p.match(account.platform.urlRegex));
if (filterUrls.length) { /* start workflowCampaign with {urls: filterUrls} */ }
continue;   // ← an account that consumed the link lane never sees the search lane

// :153-155 — lane B: search URL must match ONE of the platform's regex list
const matchUrl = searchUrl.find((p) =>
  (account?.platform?.searchURL?.regex || []).some((r) => p.match(r)));
```

**Flow:** resolve the workflow tenant-scoped (`getWorkflowAccounts`, error envelope on miss) → fan out over its bot-account children (`Promise.all` of `getBot(JSON.parse(node.data||'{}').account.id)` joined with `botList.find(p => p.identifier === bot.platform)`) → for EACH account: if `link[]` present, normalize every URL to that platform's www convention and keep only URLs matching `platform.urlRegex`, then start ONE `workflowCampaign` carrying all surviving urls; else try `searchUrl`: first search URL matching any of `platform.searchURL.regex[]` starts ONE `workflowUploadLeads` for that bot. `importURLList` closes the loop by advertising the same metadata to clients: uniq'd platforms → `botList.find(identifier && urlRegex)` sorted by `provider.order` → `{source, flags}` pairs (RegExp serialized as plain data, recurs with provider-tool-contracts), plus `searchLink` entries with description + regex arrays.
**Invariant:** (1) lane choice is evaluated **per account**, not per request — the same submission can legitimately feed campaign jobs to one bot and nothing to another whose `urlRegex` matches none of the links; the post-lane-A `continue` means link-matching accounts never fall through to the search lane. (2) Ingestion eligibility is executable provider metadata (`urlRegex` / `searchURL.regex` on `botList` entries) — NOT hardcoded per-endpoint logic; adding a platform automatically extends ingestion. (3) The two lanes carry different search-attribute scopes: campaign runs are org-visible only, while scrape runs are triple-keyed `workflowId+organizationId+botId` because each scrape belongs to exactly one bot (asymmetry mirrors campaign-fan-out-join vs temporal-multitenant-control-plane). (4) Both lanes use random-suffix multi-run ids and `retry.maximumAttempts:1` (see campaign-launch-guards invariant 3). (5) `importURLList`'s advertised `{source, flag}` pairs are the SAME regex objects used for filtering — client-side preview can never drift from server-side matching within one pin.
**Probe:** no upstream test runner exists (spec/test count = 0, re-verified this pass). Deterministic source pin executed: `grep -n "isWWW\|url-leads-\|searchURL\|urlRegex\|normalizeUrlSafe" workflows.service.ts` → :105, :106, :118, :154, :168, :211, :219, :220, :226, :234, :235, :236 exactly as cited.
**Retrieve (executed):** `search_graph({project:"growchief", query:"uploadLeads importURLList normalizeUrlSafe workflowUploadLeads"})` → rank#3 `uploadLeads` :86–189, rank#5 `importURLList` :191–244, plus `normalizeUrlSafe` shared/both/utils/url.normalize.ts:15–38 and `workflowUploadLeads` :16–68 line-exact.

## Verdict
Adopt metadata-driven dual-lane ingestion: declare per-provider URL eligibility as regex data, normalize to each provider's host convention, filter per account, and give scrape-style ingestion narrower (per-bot) routing attributes than campaign fan-out. Adapt regex serialization to your stack (here deliberately split into `{source, flags}` so clients rebuild without receiving RegExp objects). Omit the LinkedIn/X-specific regex tables themselves (rotating product constants — read them from `bot.list.ts` at port time). Coverage caveat: all four cited paths returned `no_recorded_issue` + `metadata_match`, `generation_matches: true`; static callers_total = 0 on `uploadLeads` (DI controller edge) — liveness verified by grep at `workflows.controller.ts:44–57`. No behavioral runner upstream.
