<!-- capsule-v2 -->
# Reference normalization gate — how do you stop a user-supplied identifier from becoming another page's URL?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How must free-text person/company/id inputs be normalized before they are interpolated into navigation URLs?

## Parse-or-refuse, idempotent, escape-proof, locale-proof
**Path/Symbol:** `linkedin_mcp_server/scraping/identifiers.py:normalize_person_identifier` (:307), `normalize_company_identifier` (:355), `normalize_opaque_id` (:402), `_numeric_tail` (:385), `_usable` (:161), `_linkedin_segments` (:194).
**Signature:** `def normalize_person_identifier(value: str, *, allow_self_alias: bool = False) -> str`; `def normalize_opaque_id(value: str, *, field: str, route: tuple[str, ...] = (), numeric: bool = False) -> str`.
**Data Shape:** Accepts bare identifiers OR full URLs (slugged forms included); returns the canonical reference; raises `InvalidReferenceError` carrying the exact correction for the caller.

### Decisive source
```text
Why refuse rather than coerce (docstring): "letting it through spends a
navigation and returns ANOTHER PAGE'S TEXT as a profile." Refusing costs
nothing; a bad value costs a full page load to discover.

Traversal is the threat model, not typos: job_id="../../feed" builds
/jobs/view/../../feed/, which the browser RESOLVES TO /feed/ before asking
for anything. Hence _usable() rejects dot-segments and percent-encoded
escapes that hide them ("refuses syntax the escapes were hiding"), plus
exact-dot segments and profile-path escapes — all direct-tested.

Reserved-alias rule: "me" is LinkedIn's alias for the SIGNED-IN MEMBER.
normalize_person_identifier refuses it UNLESS allow_self_alias=True, which
only get_my_profile passes: it navigates /in/me/ and reads the identifier
back out of the redirect, so refusing there would tell the one tool that owns
the alias to call itself.

Idempotence: applying twice along a call chain is harmless — normalize
(normalize(x)) == normalize(x) — so middleware layers can re-validate freely.

Slugged numeric ids (_numeric_tail): LinkedIn serves BOTH /jobs/view/1967281839/
and /jobs/view/<title>-at-<company>-1967281839/ (both 301 to the same
destination — measured). regex fullmatch r"[\w-]*?-(\d+)" extracts the trailing
digit run; applied ONLY to segments taken OUT OF A URL under the id's own
route. A BARE argument stays strictly numeric when numeric=True: there the
words are not a slug LinkedIn wrote, they are a wrong value.

Locale independence: identifiers say the same thing in every interface
language — unlike page words (see core/auth capsule), which is why validation
keys on structure and never on display text.
```

**Flow:** strip → empty? raise with correction → try parse as LinkedIn URL under the wanted route (wrong route ⇒ "that is a link but not an X" error) → else treat as bare identifier → escape/dot-segment checks → reserved-alias check → canonical form out. Opaque ids additionally allow route-prefixed references (server-printed `/messaging/thread/2-abc/` handed straight back) and numeric-tail extraction.
**Invariant:** Every externally-supplied reference crosses this gate before touching a URL template; the function set is total over its input grammar (either canonical value or typed error naming the fix).
**Probe:** `grep -c 'fullmatch' linkedin_mcp_server/scraping/identifiers.py` → 1; `grep -c 'def test_refuses_a_value_that_would_escape_the_profile_path' tests/test_identifiers.py` → 1; suite `tests/test_identifiers.py` (539L added in drift): idempotence (:66), alias refusal in every form (:140), malformed escapes inside full URLs (:157).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "normalize_person_identifier numeric_tail opaque id", limit: 5 });
```

## Verdict
Adopt parse-or-refuse normalization with traversal-proof escaping for any identifier interpolated into navigable URLs. Adapt grammar/reserved tokens to your domain. Omit LinkedIn-specific routes.
