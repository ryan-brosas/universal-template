<!-- capsule-v2 -->
# Locale-proof picker detection — how do you recognize a localized interstitial the word table cannot cover?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** Where does a structural (language-independent) check belong in a layered barrier detector?

## Structural id check runs BEFORE the cheap-exit, ahead of all text matching
**Path/Symbol:** `linkedin_mcp_server/core/auth.py:_detect_auth_barrier` (:108), structural branch (:129-137), selector `_REMEMBER_ME_CONTAINER_SELECTOR = "#rememberme-div"` (:36); quick/full split `detect_auth_barrier_quick` vs `detect_auth_barrier` (:96-106).
**Signature:** `async def _detect_auth_barrier(page: Page, *, include_body_text: bool) -> str | None`.
**Data Shape:** Detection ladder output = typed reason string (`"auth blocker URL: …"`, `"login title: …"`, `"account picker: #rememberme-div"`, `"auth barrier text: <markers>"`) or None.

### Decisive source
```text
The comment IS the design record:
    # English only, and knowingly so: these are the words the account picker
    # uses, and the words change with the interface language while nothing
    # about the page announces which one is in play. The structural check below
    # carries the locales this table does not, which is why it runs first.
    ...
    # An id, so it says the same thing in every interface language ... The rest
    # of the codebase already reads this container as the picker; here it is
    # the only signal that survives a locale change, because the URL of an
    # in-place picker IS the page that was asked for and its title is that
    # page's title.
    #
    # Ahead of the quick check's exit, and not behind it, because the two
    # signals it does read are exactly the two this page defeats. The quick
    # check runs after every navigation, so a picker served in a locale the
    # table below does not cover reached every scraping tool as page text.
    try:
        if await page.locator(_REMEMBER_ME_CONTAINER_SELECTOR).count() > 0:
            return f"account picker: {_REMEMBER_ME_CONTAINER_SELECTOR}"
    except Exception:
        logger.debug("Could not count remember-me containers", exc_info=True)

Ladder order and why: URL pattern (free) → title patterns (cheap; defeats an
in-place picker whose URL/title are the requested page's own) → STRUCTURAL id
count (one locator count; survives every locale) → body-text marker groups
(expensive AND-joined phrases; only in the FULL variant). include_body_text=False
exits after the structural check — the body read is what the quick check exists
to skip, so the structural test must precede that exit rather than hide behind it.

Failure isolation: a broken locator counts as "no signal" (debug log), never a
detection failure — a detector must not become the outage it guards against.
```

**Flow:** every navigation → quick ladder (URL → title → structural id → None) on hot paths; full ladder adds normalized-whitespace body scan with AND-grouped phrase markers when the quick check found nothing but suspicion remains.
**Invariant:** Language-independent evidence is checked before language-dependent evidence can end the scan, and the cheapest checks always run first — a structural signal may rescue what the word tables miss, but never at the price of skipping the free URL check.
**Probe:** `grep -c '_REMEMBER_ME_CONTAINER_SELECTOR' linkedin_mcp_server/core/auth.py` → 4; `grep -c 'account picker' linkedin_mcp_server/core/auth.py` → 2; direct tests: `tests/test_core_auth.py::test_a_localized_account_picker_is_still_a_barrier` (:137), `test_the_quick_check_asks_the_page_for_a_picker` (:171).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_feed_auth_succeeds raise_if_proxy_configured auth barrier", limit: 5 });
```

## Verdict
Adopt structural-before-textual ordering with cheap-first layering for any localized-UI classifier. Adapt the structural anchor to your target's stable DOM ids. Omit LinkedIn's specific marker phrases.
