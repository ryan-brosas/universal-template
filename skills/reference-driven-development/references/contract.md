# Reference Contract — project-local implementation prior art

The single contract for using external evidence as prior art. Procedures live in
`skills/reference-driven-development`; this file owns the rules. Tool selection
(`evidence-router`) and acquisition mechanics (`web-reference`, clone commands)
live in their owners.

## Reference kinds

- **Code reference**: a repository checkout at `<project>/reference/<repo>/` —
  implementation evidence (source, tests).
- **Web reference**: a capture of a live website at
  `<project>/reference/web/<site>/` — visual and interaction evidence
  (rendered HTML, CSS, screenshots, archives), produced by the `web-reference`
  skill; its exact manifest and path contracts can be checked by the optional `scripts/web-reference-manifest.py` maintainer tool.
- **Approved design artifact**: an approved design state (for example an
  OpenDesign project) — target design evidence for the intended visual or UX
  outcome after explicit approval; it does not override project acceptance
  gates.

All three are prior-art evidence, not acceptance authority. The same ADOPT /
ADAPT / OMIT decision applies per concern. A web reference records source,
capture date, scope, evidence inventory, and coverage gaps in its
`manifest.json`; brand assets, logos, and proprietary media are never copied
into the project.

## Authority

The current project's requirements and gates are the acceptance authority. A
reference shows how someone else solved a similar problem; this project decides
what ships. Provenance (repo, path, revision — or site URL, capture id) is
recorded in the PR's Reference / Prior Art section.

## Defaults

- **Code: one strong reference first.** Add a second only after naming the
  specific gap the first left open.
- **Frontend synthesis may combine several web references** — density from one
  site, hero composition from another, interaction from a third — when each
  contributes a named quality.
- Read the actual evidence: reference source and its direct tests for code;
  `REFERENCE.md` and the captured bundle for web. Summaries are leads, not
  evidence.

## Lifecycle

References are normally read-only, local, and disposable. Prefer
`.git/info/exclude` for local-only references instead of the shared
`.gitignore`. A reference checkout or web capture is never automatically
promoted into a skill, foundation, index, or corpus.

Active owned projects remain direct source while work is in progress. After a
stable milestone, only an explicit user decision may promote expensive,
reusable understanding into a foundation or persistent index. Completion alone
never triggers ingestion, and no promotion is the default.

**References vs foundations:** `<project>/reference/` holds actual external
code or captured frontend evidence for inspection and adaptation.
`skills/<x>-foundation/` holds reusable understanding distilled
from strong implementations (architecture, patterns, seams, pointers) in the
same filesystem tree, marked `kind: foundation`, manual, and hidden. Foundations
must stay outside operational host exposure (use the filtered route in
`../../../README.md` when the host does not enforce hidden metadata) and never
outrank the source they came from; project-local references outrank generic
foundations when both apply.

**Foundation provenance (forward rule for new or materially touched
foundations):** record portable upstream identity (`owner/repo` or canonical
URL), exact source revision (commit/tag/ref), and license when known. A
foundation explicitly promoted from owned material without upstream VCS records
`promotion: explicit-user` in its frontmatter. Machine-local checkout paths
are secondary convenience only. Keep the loader as a concise source/revision
and topic map, preserve exhaustive detail in `references/index.md`, and load one
matching capsule rather than the inventory. When a foundation points at source
that is not available locally, resolve the portable identity,
acquire or reuse it under `<project>/reference/<repo>/`, and inspect source and
tests before load-bearing claims.

## License

When materially copying implementation, inspect the upstream license and
preserve required attribution (record it in the PR's Reference / Prior Art
section). Captured web media grants no reuse rights; generated originals follow
`skills/web-reference/references/media.md`.
