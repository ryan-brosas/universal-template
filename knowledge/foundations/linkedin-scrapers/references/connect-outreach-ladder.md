<!-- capsule-v2 -->
# Connect outreach ladder — how do I send a connection request safely across LinkedIn UI variants, and what must I check BEFORE clicking?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how do I detect an already-pending invite first, survive five different Connect-button DOM layouts, handle LinkedIn's add-note modal variants, and still return the canonical profile id after redirects?

## LinkedinConnectService.process + clickConnectButton — pending-guard → method ladder → modal ladder
**Path/Symbol:** `lib/linkedin/linkedin.connect.service.ts:LinkedinConnectService.process` (:25–186); `clickConnectButton` (:260–274) dispatching `connectMethod1/3/2/4` (:227–258, :188–214, :216–221, :223–225).
**Signature:** `async process(page: Page, cdp: CDPSession, data: {message: string; url: string; extra?: {myname, mylastname, mycompany}}) -> {name, currentCompanyPicture, companyName, current_position_title, location, headline, current_position_length, url, linkedin_id}`.
**Data Shape:** input URL may be bare `/in/slug` or full; `createLinkedinLink(url, true)` canonicalizes to `https://www.linkedin.com/in/<slug>` (trailing-slash stripped). Return `linkedin_id` is derived from the POST-CLICK `window.location.href` through `createLinkedinLink(newUrl, false)` — never from the input.

### Decisive source
```ts
// 1) PENDING GUARD — selector probe + multilingual TEXT probe, throw before any click
const pending = await page.$(
  "button.pv-s-profile-actions--connect:disabled, .message-anywhere-button.artdeco-button--primary");
const pending2 = await page.evaluate(() => {
  return !!Array.from(document.querySelectorAll("button")).find(
    (p) =>
      p?.textContent?.toLowerCase()?.trim()?.indexOf("pending")! > -1 ||
      p?.textContent?.toLowerCase()?.trim()?.indexOf("en attente")! > -1 ||   // fr
      p?.textContent?.toLowerCase()?.trim()?.indexOf("待處理")! > -1 ||        // zh
      p?.textContent?.toLowerCase()?.trim()?.indexOf("ausstehend")! > -1 ||    // de
      p?.textContent?.toLowerCase()?.trim()?.indexOf("nawiąż kontakt")! > -1 ||// pl
      p?.textContent?.toLowerCase()?.trim()?.indexOf("in sospeso")! > -1);     // it
});
if (pending || pending2) {
  throw new LinkedinErrors("Connection is already pending");
}
// 2) EMAIL-VERIFICATION WALL — right after clicking connect
const email = await page.$("#email");
if (email) { throw new LinkedinErrors("Linkedin Prompt Email Verification"); }
// 3) MODAL LADDER — pill-choice group is OPTIONAL (3s timeout swallowed);
//    actionbar button count decides whether "Add note" must be clicked first
if (total === 3) { await this.moveAndClick(page,
  ".artdeco-modal__actionbar > button:nth-child(1)"); }  // Add note
await this.moveAndClick(page, ".artdeco-modal__actionbar > button:nth-child(1)");
try { await page.waitForSelector("textarea", { timeout: 2000 }); }
catch (err) { /* re-click nth-child(1) then wait unbounded */ }
// 4) SEND enabled only when textarea content lifted the disabled class
await page.waitForFunction(() => {
  const find = document.querySelector(".artdeco-modal__actionbar > button:nth-child(2)");
  return (find &&
    find?.getAttribute("class")?.indexOf("artdeco-button--disabled") === -1);
});
```
Method ladder (`clickConnectButton`, :260–274) is strict try/catch nesting in FIXED order: `connectMethod1` (find button by multilingual innerText — connect/conectar/collegati/se connecter/建立關係/kur/vernetzen — then click by resolved id; throws empty string if not found) → `connectMethod3` (top-card dropdown trigger, hover-scroll to one of four connect selectors, JS `.click()`) → `connectMethod2` (direct selector incl. modern `.pvs-profile-actions__action` minus follow/message buttons) → `connectMethod4` (`li-icon[type=connect] + span` legacy).

**Flow:** gotoUrl(canonical profile) → waitForLoader + top-card selector → pending guard (selector OR text) → extractInformation → clickConnectButton (ladder) → email-verification wall check → optional pill-choice modal ("Add reason", dismissed via nth-child(1)) → if message: actionbar-count modal ladder, type templated message (`generateMessage`) at delay 30 → wait send-enabled → click nth-child(2) → swallow 1000ms modal-gone race → capture post-action href → return dossier keyed by canonical linkedin_id.
**Invariant:** the pending check runs BEFORE any state-changing click (a second invite to the same prospect is an account-risk event, not a retry case); the returned `linkedin_id` must come from the browser AFTER the request (redirects/vanity-URL normalization happen server-side — the input string lies). The commented invariant in-source applies to visit/connect alike: "if we don't do this, we would not know about connection requests approved". Usage shape pinned by `lib/test.example.ts`: `loadCursor` → `login` → `page.setCookie({name:"li_at"...})` → `services.connect.process`.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchor `clickConnectButton` resolves :260–274 exactly (unique hit), `process` :25–186.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "clickConnectButton connectMethod pending", limit: 5 });
// resolves LinkedinConnectService.clickConnectButton :260–274 + process :25–186
```

## Verdict
Adopt the order pending-guard → click-ladder → verification-wall → modal-ladder → post-redirect id capture as THE safe connect flow; adapt the multilingual needle lists and CSS selectors (they track live LinkedIn markup and locale mix — re-verify before production); omit `connectMethod4`'s legacy icon selector unless porting to old-layout targets. Contrast: EasyApplyJobsBot's run orchestration clicks apply flows job-side, this guards people-side invites — both share "check pre-existing state before mutating" discipline.
