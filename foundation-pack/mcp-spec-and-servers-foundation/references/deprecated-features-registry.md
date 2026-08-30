<!-- capsule-v2 -->
# Deprecated-features registry — which features must new implementations NOT adopt, and what are the migration paths?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What is the authoritative Deprecated-state list under SEP-2596, and what does "deprecated" actually obligate?

## Six-row registry + the lifecycle rule
**Path/Symbol:** `docs/specification/2026-07-28/deprecated.mdx` (whole page: policy :7–17; table :22–35; Removed section :37–42); policy source `docs/community/feature-lifecycle.mdx` (Active → Deprecated → Removed states); changelog cross-refs (`docs/specification/2026-07-28/changelog.mdx` "Deprecated" section).

**Signature:** registry rows = `{feature, deprecation SEP/PR, deprecated-in revision, migration path, earliest removal}`. Current six rows: **Roots** / **Sampling** / **Logging** (all SEP-2577, deprecated in 2026-07-28, earliest removal first revision on/after 2027-07-28), **Dynamic Client Registration** (PR #2858 → migrate to Client ID Metadata Documents), `includeContext:"thisServer"/"allServers"` (SEP-2596, deprecated 2025-11-25, removal follows Sampling), **HTTP+SSE transport** (SEP-2596; deprecated since 2025-03-26; earliest removal three months after SEP-2596 reaches Final).

**Data Shape:** a Deprecated feature REMAINS part of the specification — fully functional during the window — but new implementations SHOULD NOT adopt it and existing ones SHOULD migrate before earliest removal (:12–15). Earliest removal is when a feature becomes *eligible* for removal; actual removal is a Core Maintainer decision during release prep and may be later (:16–17). The page itself is a DERIVED view kept consistent with per-feature notices and changelog entries, which are the NORMATIVE records (:19–20). Removed section currently empty — nothing has yet been removed under this policy (:37–39).

### Decisive source
```md
# docs/specification/2026-07-28/deprecated.mdx:12-15
A Deprecated feature remains part of the specification but is scheduled for
removal: new implementations **SHOULD NOT** adopt it, and existing
implementations **SHOULD** migrate before the feature's earliest removal.
```
Migration paths verbatim (:26–31): Roots ⇒ pass directories/files via tool parameters, resource URIs, or server configuration; Sampling ⇒ integrate directly with LLM provider APIs; Logging ⇒ log to stderr (stdio) or OpenTelemetry; DCR ⇒ Client ID Metadata Documents; includeContext ⇒ omit the field or use `"none"`; HTTP+SSE ⇒ Streamable HTTP.

**Flow:** building a new server/client? consult this registry BEFORE adopting any legacy surface — Roots/Sampling/Logging appear in older tutorials and SDKs but carry a 2027 removal horizon; serving old clients? keep deprecated features working through the window while offering the migration path. The 12-month minimum deprecation window (policy) means "deprecated in 2026-07-28" ⇒ eligible no earlier than 2027-07-28.

**Invariant:** deprecation is a STATE with an obligation gradient (SHOULD NOT adopt new / SHOULD migrate existing / MUST still interop during window) — not a removal notice. A porter who reads "deprecated SEP-2577" as "delete the code now" breaks legacy-client interop; one who adopts Roots in NEW code accrues scheduled-removal debt. The derived-view caveat matters when dates conflict: per-feature notices win over this page.

**Probe:** no runtime tests in the spec repo; machine-checkable anchors are the changelog's Deprecated section and each row's linked SEP document under `docs/seps/` (e.g. `2577-deprecate-roots-sampling-and-logging.mdx`). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern` over the SEP/deprecation identifiers the registry rows cite):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'Deprecated|deprecated' --limit 15
```

## Verdict
Adopt the registry as a build-time adoption gate (never adopt Deprecated surfaces in new implementations; plan migrations against earliest-removal dates) and the state-machine vocabulary Active/Deprecated/Removed for your own features; adapt migration mechanics to your host; omit any claim that deprecated features are already removed — the Removed section is empty at this pin.
