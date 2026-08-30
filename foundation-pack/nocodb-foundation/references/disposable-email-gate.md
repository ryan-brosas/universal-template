<!-- capsule-v2 -->
# disposable-email gate — how does a 4,000-domain blocklist stay exact-match safe while still catching subdomain farms?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the matching contract of `isDisposableEmail` — and why does a naive substring or endsWith check against the raw list both produce wrong verdicts?

## Exact-list + one-dot-wildcard two-tier matcher

**Path/Symbol:** `packages/nocodb/src/helpers/isDisposableEmail.ts:isDisposableEmail` (:4019–4031), `disposableEmailDomains` array (:1–4016), `wildcardHostname` sub-list.
**Signature:** `isDisposableEmail(email: string): boolean | undefined` — truthy on match, UNDEFINED (not false) otherwise; callers treat it as boolean.
**Data Shape:** TWO compiled-in arrays (no runtime fetch): the main list is ~3,600 literal domains (:1–4015); a separate `wildcardHostname` array (:3616–…) holds ~400 domains that may appear only as PARENTS of subdomains — dynamic-DNS/dynamic-alias families (`3utilities.com`, `zapto.org`, anonaddy twins) and shared-suffix traps (`web.id`, `.buzz`/`.tk` subdomain farms).

### Decisive source
```ts
// :4018-4031 — the entire function
// validate is email is temporary disposable email
export function isDisposableEmail(email: string) {
  const hostName = email.split('@')[1];
  // check for exact host name match
  if (disposableEmailDomains.includes(hostName)) return true;
  // check for wildcard host name match
  if (wildcardHostname.some((domain) => hostName.endsWith('.' + domain))) return true;
}
```

**Flow:** split on the LAST-free first-@ semantics of split('@')[1] → tier 1 exact `includes` against the big list → tier 2 wildcard: host must END WITH `.<suffix>` so `foo.web.id` matches but bare `web.id` does NOT (it's a real country-code TLD — the list deliberately contains it only as a wildcard parent). No lowercasing, no punycode handling, no MX lookup — pure lexical gate at signup/invite time.
**Invariant:** (1) Tier 1 is EXACT match — a listed domain matches only the bare host itself, never subdomains. (2) Tier 2's `'.' + domain` prefix is load-bearing: it matches any depth of subdomain under a wildcard parent while never letting a bare wildcard-parent host (or an unrelated lookalike like `notzapto.org`) match; porters who switch tier 2 to plain `endsWith(domain)` flag every user whose host merely ENDS with a listed string. (3) The return type is undefined-not-false; strict callers (`if (!isDisposableEmail(x))`) are fine, `=== false` callers are broken.

### Porting traps (each verified against source)
- The list contains entries like `web.id`, `co.uk`-style public suffixes ONLY in the wildcard family — moving entries between tiers changes verdicts for bare-domain users.
- In-file anchors: `grep -c 'wildcardHostname' src/helpers/isDisposableEmail.ts` → 2 (decl + use); `grep -c "disposableEmailDomains.includes" …` → 1; file is 4,031 lines / 72KB — the DATA dominates; the logic is 14 lines.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n "endsWith('.' + domain)" src/helpers/isDisposableEmail.ts | cut -d: -f1` → `4028` and `sed -n '4019,4031p' src/helpers/isDisposableEmail.ts | grep -c "split('@')"` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "isDisposableEmail wildcardHostname disposableEmailDomains", limit: 10 });
```
Resolves `isDisposableEmail` :4019-4031 rank-1.

## Verdict
Adopt the two-tier matcher and the dot-prefixed wildcard rule verbatim; refresh the domain data from your own source (it ages); omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
