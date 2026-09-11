# Foundations

Cold, source-specific implementation evidence: architecture, seams, and edge
cases distilled from one identified upstream revision. Not instructions, not
procedures, and never loaded automatically. Current project source, tests,
requirements, and runtime behavior outrank everything here.

## Shape

    knowledge/foundations/<name>/
      README.md            provenance, recorded revision, topic map, retrieval rule
      references/index.md  full inventory, provenance record, capsule map
      references/*.md      capsules, the actual evidence

`README.md` keeps frontmatter with `name`, `description`, and `kind: foundation`
so the pack index can show a cue. This tree sits outside host skill discovery, so
no invocation fields are needed and the directory name drops the `-foundation`
suffix it carried as a skill leaf.

## Retrieval

Start at `../../skills/foundation-pack/SKILL.md`, choose one category, open one
foundation, then read one capsule. Revalidate the capsule's cited source and
revision before relying on it. Do not bulk-load a category or an inventory.

## Adding one

Follow `../../skills/writing-skills/references/foundation-kind.md`, then add the
directory to the one matching file under `categories/`. Do not add citations,
source pins, or evidence indexes anywhere else in the repository.
