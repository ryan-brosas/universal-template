<!-- capsule-v2 -->
# Component-first structure + 3-tier layering — how do you lay out a service so business borders are real and the web layer stays replaceable?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What directory topology does the repo prescribe, and which dependency direction makes entry-points swappable?

## Components own their whole vertical slice; three tiers inside
**Path/Symbol:** `sections/projectstructre/breakintcomponents.md` (good/bad trees :37-58) + `sections/projectstructre/createlayers.md` (tier tree :7-15, layer definitions :21-27).
**Signature:** filesystem contract:
```bash
my-system/
├─ apps/                # business components (bounded contexts)
│  └─ orders/  ├─ package.json  ├─ entry-points/{api,message-queue}  ├─ domain/  ├─ data-access/
└─ libraries/           # generic cross-component code (logger, authenticator), each its OWN package.json
```
**Data Shape:** component = self-contained logical app with its own API/logic/data-access/tests. Consumption across components ONLY via public interface/API. Anti-pattern tree (:48-58): top-level `controllers/ services/ models/` grouped by technical role — module-a controller calling module-b service means "no clear modularity borders" (README 1.1 Otherwise).

### Decisive source
```text
// createlayers.md :21-27 — tier responsibilities (abridged)
Entry-points: adapt payload (e.g., JSON) to app format incl. first
  validation, call domain, return response — "just an adapter".
Domain: protocol-agnostic plain-JS objects in/out; services, DTOs,
  clients; calls data-access.
Data-access: repository pattern; returns/gets plain objects, DB agnostic;
  owns query builders, ORMs, drivers.
```

**Flow:** request enters an entry-point adapter → validated + converted to plain object → domain logic executes (may call data-access) → response shaped back at the edge. Web/queue/scheduled entry-points are interchangeable because domain never sees transport types.
**Invariant:** (1) request/response objects NEVER pass into domain/data-access — violation blocks reuse by tests, cron, queues (README 1.2 Otherwise). (2) Cross-component imports touch only the component's public interface. (3) Utilities live under `libraries/` as independently package-able units; once ≥2 deployed components need them, wrap and publish privately — `utility-wrap-private-package`.
**Probe:** no runner upstream. Deterministic probe: both files contain good/bad ASCII trees (`grep -c 'entry-points\|data-access' sections/projectstructre/createlayers.md` ≥ 3).

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "data-access", "limit": 10}'
# resolves `sections/projectstructre/breakintcomponents.md`, `sections/projectstructre/createlayers.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the two-level contract (components-first at system root, 3 tiers per component) for any service layout regardless of language. Adapt folder names and the packaging tooling (npm linking / ts-paths / registry). Omit MVC-vs-clean-architecture debate details — the doc's own verdict is "3-tier is the simplest separation that works."
