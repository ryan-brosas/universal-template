<!-- capsule-v2 -->
# Profile-views private mode — how do I harvest "who viewed my profile" when LinkedIn hides some viewers' names?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** how does the analytics list stay schema-total when an entity card has NO name span because the viewer browses in private mode?

## LinkedinProfileViewsService.process — drain, then one-pass map with a count-row fallback
**Path/Symbol:** `lib/linkedin/linkedin.profileViews.service.ts:LinkedinProfileViewsService.process` (:21–62; private branch :38–50).
**Signature:** `process(page: Page, cdp: CDPSession): Promise<Array<People>>` where `People = { name: { firstName, lastName }, profilePicture?, count?, countString? }`.
**Data Shape:** named viewer row → `{ name: {firstName: words[0], lastName: words[1]}, profilePicture: img.src }`; anonymous row → `{ name: { firstName: "Private Mode", lastName: "Private Mode" }, countString: "<n> views"-style first word }`.

### Decisive source
```ts
let x = person?.querySelector("span > span");
let name = x?.textContent.split(" ");
if (!name) {
  let countString = person.textContent.trim().split(" ")[0];
  // BUG: The following two lines give and error because the string might not have been resolved yet
  // let count = parseInt(countString);
  return {
    name: { firstName: "Private Mode", lastName: "Private Mode", countString },
  };
}
let picNode = node.querySelector("img")?.getAttribute("src");
return { name: { firstName: name[0], lastName: name[1] }, profilePicture: picNode };
```

**Flow:** `page.goto("/analytics/profile-views/")` → wait `.member-analytics-addon-entity-list__entity` → `autoScroll(page)` drains the lazy list until scrollTop stalls → timer(2000) → ONE `page.evaluate` maps EVERY entity card → rows returned together.
**Invariant:** collection happens ONCE, AFTER the scroll drain — never mid-scroll, so no partial sets; a missing name degrades the ROW into a count-bearing placeholder instead of dropping it (row count == viewer-card count, always); upstream's own BUG comment warns `parseInt(countString)` crashes on unresolved strings — the disabled lines are load-bearing documentation.
**Probe:** no upstream tests (blocker). Deterministic anchor: the `Private Mode` fallback literal + `member-analytics-addon-entity-list__entity` selector at HEAD — verification.md probe P2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "profileViews private mode", limit: 5 });
```
Resolves `LinkedinProfileViewsService.process` :21–62 + `People`.

## Verdict
Adopt drain-then-single-evaluate and the placeholder-row fallback (schema-total analytics beats dropping anonymous viewers); adapt field selectors; omit the naive `words[0]/words[1]` split for multi-part names — port it with a proper name parser and NEVER enable the commented `parseInt` without guarding the string.
