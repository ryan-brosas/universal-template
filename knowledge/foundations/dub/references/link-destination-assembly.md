<!-- capsule-v2 -->
# Destination URL assembly — how do query params flow from the short link onto the final destination without leaking internal params, and what per-integration params get injected?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Which search params from the visitor's URL overwrite the target's, which internal ones are stripped, and where do clickId / via / platform-specific params get added?

## getFinalUrl param merge + internal-param strip list
**Path/Symbol:** `apps/web/lib/middleware/utils/get-final-url.ts:getFinalUrl` (13-135).
**Signature:** `getFinalUrl(url: string, {req: NextRequest, clickId?: string, via?: string}): string`.
**Data Shape:** internal params: `dub-no-track` (suppress tracking), `redir_url` (`REDIRECTION_QUERY_PARAM`, override destination), `qr=1` (QR-detect marker, stripped before handoff), `skip_deeplink_preview=1`. Injected: `dub_id`, `via`, `client_reference_id=dub_id_<clickId>`, AppsFlyer `pid/clickid/c/af_siteid`, Singular `cl/ua/ip/wpcn/wpcl`.

### Decisive source
```ts
// 1. redir_url can REPLACE the configured destination (must still be a valid URL)
const redirectionUrl = getUrlFromStringIfValid(
  searchParams.get(REDIRECTION_QUERY_PARAM) ?? "");
const urlObj = redirectionUrl ? new URL(redirectionUrl) : new URL(url);

// 2. Stripe payment-link convention: opt-in flag swaps for the documented param
if (urlObj.searchParams.get("dub_client_reference_id") === "1") {
  urlObj.searchParams.set("client_reference_id", `dub_id_${clickId}`);
  urlObj.searchParams.delete("dub_client_reference_id");
} else if (!searchParams.has("dub-no-track")) {
  urlObj.searchParams.set("dub_id", clickId);        // default attribution param
}

// 3. merge loop: visitor params OVERWRITE target params, minus internals
if (searchParams.size === 0) return urlObj.toString();
for (const [key, value] of searchParams) {
  if (["dub-no-track", REDIRECTION_QUERY_PARAM].includes(key)) continue; // never forwarded
  urlObj.searchParams.set(key, value);
}

// 4. strip marker-only params before handoff
if (urlObj.searchParams.get("qr") === "1") urlObj.searchParams.delete("qr");
if (urlObj.searchParams.get("skip_deeplink_preview") === "1")
  urlObj.searchParams.delete("skip_deeplink_preview");
```

**Flow:** base = target or redir override → partner links add `via=<key>` → clickId attached unless `dub-no-track` (or swapped to `client_reference_id` for Stripe) → integration branches rewrite param names for AppsFlyer/Singular/Play-Store referrer → visitor params merged with overwrite semantics → internal markers stripped.
**Invariant:** internal control params NEVER reach the destination host — the strip list is checked in the merge loop AND again after it (qr/skip_deeplink_preview can arrive inside a redir_url). Overwrite direction is visitor-wins: short-link query beats target defaults, so campaigns can re-target a link per placement. `dub_client_reference_id=1` is an opt-in protocol flag consumed and removed, never passed through.
**Probe:** no upstream unit test (coverage caveat — exercised only via integration redirect tests). Deterministic probe: assert `?dub-no-track=1&foo=bar` on a link → destination has `foo=bar`, no `dub-no-track`, no `dub_id`; assert `qr=1` stripped even when arriving via redir_url.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getFinalUrl REDIRECTION_QUERY_PARAM dub-no-track client_reference_id", limit: 10 });
```

## Verdict
Adopt: explicit internal-param denylist enforced at merge time AND post-merge, visitor-wins overwrite, opt-in swap protocols for third-party conventions, single function owning all destination mutation. Adapt injected param names/integrations to your stack; keep the "one assembler" rule. Omit AppsFlyer/Singular/Play branches if you have no MMP integrations.
