# Reference Contract: prior art as evidence

The single contract for using external evidence as prior art. Procedures live in
`knowledge/playbooks/reference-driven-development`; this file owns the rules. Tool
selection (`evidence-router`) and acquisition mechanics (`web-reference`) live in
their owners.

## Reference kinds

- **Code reference**: a read-only repository checkout at `<project>/reference/<repo>/`,
  or the equivalent source read live from an indexed repository or fetch. The
  evidence is the implementation (source, tests), wherever it is read from.
- **Web reference**: a capture of a live website at `<project>/reference/web/<site>/`:
  visual and interaction evidence (rendered HTML, CSS, screenshots, archives),
  produced by the `web-reference` skill; inspect its manifest and paths with
  native JSON and filesystem tools against `../../web-reference/references/storage.md`.
- **Approved design artifact**: an approved design state (for example an
  OpenDesign project), target design evidence for the intended visual or UX
  outcome after explicit approval; it does not override project acceptance gates.

All three are prior-art evidence, not acceptance authority. The same ADOPT /
ADAPT / OMIT decision applies per concern. A web reference records source,
capture date, scope, evidence inventory, and coverage gaps in its
`manifest.json`; brand assets, logos, and proprietary media are never copied
into the project.

## Authority

The current project's requirements and gates are the acceptance authority. A
reference shows how someone else solved a similar problem; this project decides
what ships. Provenance (repo, path, revision, or site URL and capture id) is
recorded in the PR's Reference / Prior Art section.

## Defaults

- **Code: one strong reference first.** Add a second only after naming the
  specific gap the first left open.
- **Frontend synthesis may combine several web references** (density from one
  site, hero composition from another, interaction from a third) when each
  contributes a named quality.
- Read the actual evidence: reference source and its direct tests for code;
  `REFERENCE.md` and the captured bundle for web. Summaries are leads, not evidence.

## Retention and disposal

References are read-only, local, and disposable; a live indexed read leaves no
artifact at all. Prefer `.git/info/exclude` for local-only checkouts instead of
the shared `.gitignore`. Git history and current source are the durable record.

## License

When materially copying implementation, inspect the upstream license and
preserve required attribution (record it in the PR's Reference / Prior Art
section). Captured web media grants no reuse rights; generated originals follow
`knowledge/playbooks/web-reference/references/media.md`.
