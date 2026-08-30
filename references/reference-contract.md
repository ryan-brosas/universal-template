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
  skill and validated by `scripts/web-reference-manifest.py`.
- **Approved design artifact**: an approved design state (for example an
  OpenDesign project) — target design evidence, authoritative only after
  explicit approval.

All three are evidence, never authority. The same ADOPT / ADAPT / OMIT decision
applies per concern. A web reference records source, capture date, scope,
evidence inventory, and coverage gaps in its `manifest.json`; brand assets,
logos, and proprietary media are never copied into the project.

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
`.gitignore`. A reference is never automatically promoted into a skill,
foundation, index, or corpus; the legacy `*-foundation` leaves are frozen in
`foundation-pack/` and retired over time, and no new foundations are created.

## License

When materially copying implementation, inspect the upstream license and
preserve required attribution (record it in the PR's Reference / Prior Art
section). Captured web media grants no reuse rights; generated originals follow
`skills/web-reference/references/media.md`.
