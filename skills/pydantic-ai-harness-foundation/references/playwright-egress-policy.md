<!-- capsule-v2 -->
# Browser egress policy: IDNA-exact host matching, resolve-first private-address block, two-layer enforcement

## Source / Question
`pydantic_ai_harness/playwright/_toolset.py:363–727, 1315–1382` @ `main@f971198` — An agent-driven browser needs domain allowlisting AND an SSRF-class private-address block that survives Unicode hosts, trailing dots, backslash URLs, and names pointing at reserved IPs. Where does each check run, and why is DNS resolution part of the verdict?

## Path / Symbol
`playwright/_toolset.py` — `_to_idna` (:363–383), `_url_host` backslash/hostless rule (:386–399), `is_blocked_address` (:402–427), `_resolve_host` + cache (:439–491), `RequestKind` + `_request_kind` (:526–563), `EgressRequest` (:566–585), `DEFAULT_ALLOWLIST_REACH={navigation,data}` (:535), `_DATA_RESOURCE_TYPES` (:545), `EgressPolicy.refuse/_matches/needs_resolution/describe/enforced` (:604–726), `PlaywrightBrowserSession.decide/_route_guard/_websocket_guard/_abort` (:1315–1382).

## Signature
```python
class EgressPolicy(dataclass(frozen=True)):
    allowed_domains / blocked_domains / include_subdomains=True
    block_private_addresses: bool = True
    allowlist_reach: frozenset[RequestKind] = frozenset({'navigation', 'data'})
    resolved_kinds:  frozenset[RequestKind] = frozenset(get_args(RequestKind))   # ALL kinds resolve
    def refuse(self, request: EgressRequest) -> str | None       # SYNCHRONOUS verdict
    def needs_resolution(self, request) -> bool                  # asked BEFORE refuse keeps refuse sync
async def decide(self, request) -> str | None                    # resolves host first, then refuse
```

## Data Shape
Host normalization: UTS46 non-transitional IDNA via the `idna` package because stdlib IDNA-2003 renders `faß.de` ≠ browser's `xn--fa-hia.de` (:365–371); trailing dot stripped (DNS root, not a label); any URL containing `\` treated HOSTLESS (WHATWG turns `\` into `/` — urlparse would report a host Chromium never contacts :389–392). Blocked set: localhost(+subdomains), RFC1918, loopback, link-local incl. cloud metadata 169.254.169.254, CGNAT, reserved, multicast; IPv4-mapped IPv6 classified by embedded v4 (:414–416).

### Decisive source
Unanswered-lookup FAILS CLOSED (:444–457): "whoever controls the name controls whether the lookup answers — stalling this one and then handing Chromium a private address would otherwise be a way past the block. So an unanswered lookup is a refusal." Resolution runs for EVERY kind (:591–597): "an `img` pointed at `169.254.169.254` and one pointed at a name answering with that address are the same request" — passive subresources still time-loadable to map the intranet. Allowlist bounds only navigation+data by DEFAULT (:541–543): subresources render the page, sub-frame documents carry identity/payment flows. Deny wins over allow (:609–610). `about:blank` always permitted (context start state + bounce target, :652–659). WebSocket guard exists BECAUSE `context.route` never sees sockets (:1358–1368) — permitted sockets must call `connect_to_server()` explicitly since registering a handler exits pass-through mode. Honest limits recorded twice (:410–412): Chromium re-resolves before connecting ⇒ DNS rebinding NOT closed (issue #415).

**Flow:** every request → `_route_guard` classifies kind (document=navigation only at top level; same type in a frame is `subframe`) → `decide()` resolves name→addresses (30s TTL, 256-entry clear-all cache, 2s timeout, off-loop getaddrinfo) → `refuse` verdict → abort+record reason, or continue. Second layer: after click/press/history actions, `_settle` re-checks the LANDED URL and bounces disallowed pages to about:blank.
**Invariant:** policy object owns BOTH enforcement and the description shown to the model ("instructions that promise a reach the guards do not grant" is the named failure mode, :610–612); wildcard/dot-leading allowlist entries are rejected at construction (:633–648).

## Probe (direct test)
`tests/playwright/test_playwright.py::TestCheckAllowedDomain` (:802+) — userinfo-host spoof `https://allowed.com:pass@evil.com/` rejected (:820, CVE-2025-47241 class), backslash URL rejected without opening a page (:927), trailing-dot spellings both directions (:904/:912), IDN↔punycode equivalence both directions (:832), over-long-label entry falls back without crashing (:838), `mailto:` hostless rejected under open egress (:806), empty allowlist blocks every host (:962); redirect-bounce tests :955/:1031/:1064 (blocked redirect names the refused URL from the event log, never `chrome-error://chromewebdata/`; an OLDER refusal is not blamed for the new failure).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'is_blocked_address EgressPolicy _resolve_host _route_guard'
```

## Verdict
**Adopt** the resolve-first fail-closed address block + IDNA-exact matching + kind-split allowlist for any agentic browser/web-fetch surface. **Adopt** the sync-refuse/async-resolve split (keeps `refuse` subclassable without async machinery). **Omit** the proxy-based rebinding fix (upstream hasn't shipped it either).
