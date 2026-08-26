<!-- capsule-v2 -->
# Marketplace README section skeleton — what fixed sections must a one-click platform's template README carry, and which kind of claim belongs in each?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3` (generation 2026-08-25T08:42:38Z). **Question:** How is a marketplace-facing template README structured so a prospective deployer learns what it is, what it costs, what it needs, and what the adapter does — without reading code?

## Six-part TEMPLATE_README shape
**Path/Symbol:** `TEMPLATE_README.md:1,3,9,15,17,21,25` — graph File node `railway-template-nexus3.TEMPLATE_README.md.__file__` DEFINES exactly seven Section nodes: `Deploy and Host Nexus Repository on Railway` (title-as-task), `About Hosting Nexus Repository`, `Common Use Cases`, `Dependencies for Nexus Repository Hosting` (+ subsections `Deployment Dependencies`, `Implementation Details`), `Why Deploy Nexus Repository on Railway?`.
**Signature:** Markdown only; `##`-level fixed headings in marketplace-canonical order; both detail subsections (`### Deployment Dependencies`, `### Implementation Details`) nested at `###` depth; every section ≤ 2 short paragraphs or a 3-bullet list.
**Data Shape:** each section carries ONE claim class — title = task+platform; **About Hosting** = what the product is + security posture ("stable 3.95.2 with generated admin credentials and anonymous access disabled") + consent posture ("This template does not accept legal terms for you."); **Common Use Cases** = three deployment shapes; **Dependencies → Deployment Dependencies** = exactly the runtime dependencies ("a daily-backed-up `/nexus-data` volume and Railway HTTPS"); **Implementation Details** = the adapter contract in operator language (waits for first boot → rotates via official API → disables anonymous → stores idempotency marker; one replica; ≥2 GB RAM); **Why Deploy** = platform value props (credentials, HTTPS, storage, backups, health checks, metrics, Git-driven updates).

### Decisive source
```markdown
## About Hosting Nexus Repository

Nexus Repository is a universal artifact manager for Maven, npm, NuGet, PyPI, Docker,
raw files, and other package formats. This template deploys stable 3.95.2 with generated
admin credentials and anonymous access disabled.
...
### Implementation Details

The adapter waits for first boot, rotates the generated bootstrap password through the
official API, disables anonymous access, and stores an idempotency marker. Use one
replica and at least 2 GB RAM.
```
(`TEMPLATE_README.md:3-5` and `:21-23` VERBATIM at pin.)

**Flow:** a template author fills the skeleton top-down: name the task in the title → state product identity + hardening + consent posture in About → enumerate realistic uses → declare ONLY true runtime dependencies → compress the whole adapter into Implementation Details sentences that each mirror a code step → close with platform-level value props that do NOT restate implementation claims. `README.md` is the SHORT-FORM twin of the same facts for the repo page (deploy button, version, sign-in/EULA instructions, sizing, upstream license), while factual claims themselves are governed by `docs-as-deployed-contract` — this capsule governs SECTION STRUCTURE, not claim verification.
**Invariant:** the section set is load-bearing because each answers a distinct deployer question (what/why-use/what-needed/what-will-it-do/why-this-platform); omitting Dependencies or Implementation Details leaves the deployer unable to predict cost or behavior BEFORE deploying — the two questions marketplaces surface as support tickets. The Implementation Details paragraph must stay mechanism-faithful: its four verbs are the same ladder as `entrypoint.sh:19→20→21` plus wait-for-boot, so structure drift and contract drift are detectable by reading alone.
**Probe:** deterministic pins executed this pass at pin `18e177a6`: `grep -c '^## ' TEMPLATE_README.md` = 4; `grep -c '^### ' TEMPLATE_README.md` = 2; `grep -cF 'does not accept legal terms' TEMPLATE_README.md` = 1; `grep -cF 'daily-backed-up' TEMPLATE_README.md` = 1; `grep -cF 'idempotency marker' TEMPLATE_README.md` = 1. Graph probe EXECUTED this pass: the Section census below returns 7 rows = the title-as-task section plus the six heading sections (4 `##` + 2 `###`) — byte-consistent with the grep census.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "railway-template-nexus3", query: "MATCH (s:Section)<-[:DEFINES]-(m {name:'TEMPLATE_README.md'}) RETURN s.name ORDER BY s.name" });
```
→ EXECUTED this pass, 7 rows (title section + About Hosting / Common Use Cases / Dependencies for Nexus Repository Hosting / Deployment Dependencies / Implementation Details / Why Deploy…). Note the DEFINES edges originate from the File node `TEMPLATE_README.md` (the Module node is named `TEMPLATE_README` — filtering on it returns zero rows); module source via `get_code_snippet("railway-template-nexus3.TEMPLATE_README")` verified byte-equal to checkout.

## Verdict
Adopt the six-section skeleton verbatim as the authoring checklist for any one-click platform template listing (Railway/Render/Fly/marketplace equivalents); adapt heading nouns to platform vocabulary. Omit feature-marketing beyond the Why-Deploy closing section, and never let Implementation Details diverge from the adapter's real control flow.
