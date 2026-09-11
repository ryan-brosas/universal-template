# Foundation kind

## Cold foundation

A foundation is source-specific evidence distilled from one identified upstream
or explicitly promoted owned source. It is not an operational procedure and is
never model-visible: it lives outside host skill discovery.

Its exact shape is a directory under `knowledge/foundations/`:

```text
knowledge/foundations/<name>/
  README.md            provenance, recorded revision, topic map, retrieval rule
  references/index.md  full inventory, provenance record, capsule map
  references/*.md      capsules, the actual evidence
```

`README.md` keeps frontmatter with `name`, `description`, and
`kind: foundation` so the pack index can show a cue; invocation fields are not
used. Register the new directory in the one matching file under
`knowledge/foundations/categories/`. The README identifies provenance and the
recorded revision, states that current project source, tests, requirements, and
runtime behavior outrank the projection, and points to a preserved
`references/index.md`. Treat every claim as historical rather than timeless.
Search explicitly, open the index, choose one capsule matching the active
question, and load only that capsule. Revalidate its cited source and revision
before relying on it.

A source study, `/learn`, repository index, summary, or completed project does
not create or expand a foundation automatically. Foundation promotion requires
an explicit user decision after the reusable source-specific architecture,
seams, or edge cases prove more expensive to re-derive than to preserve.

## Operational skill

An operational playbook changes how work is performed. It lives at
`knowledge/playbooks/<name>/README.md` with `title`, `summary`, and
`kind: playbook`; it is reached through one visible pack router. Its procedure,
decision process or tool contract loads on demand. Repository facts and source
summaries alone do not qualify. Only pack routers use `SKILL.md`.

`/compile-skill` may consult selected session evidence and selected foundation
capsules, but those capsules remain evidence, not instructions. Creating or
changing a procedure requires an explicit promotion request and independent
recurrence by default. A single occurrence qualifies only when explicitly
requested and unusually costly, high-risk, or difficult to recover. Facts stay
in source, references, or a foundation; deterministic expectations go to code
or gates; only the proven procedure goes into the skill loader.
