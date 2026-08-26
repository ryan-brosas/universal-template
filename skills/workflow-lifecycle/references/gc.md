# gc — workspace hygiene contract

Applies: workflow-lifecycle gc. Source prompt: ~/.agents/prompts/gc.md (when present).

## Goal
Remove workspace cruft without touching user-owned content: temp files, dead references, stale caches, duplicated knowledge — while keeping Agent Rules and Catalogs intact.

## Steps
1. Scan (read-only) for cleanup families: temp/pid files, orphaned caches, unreferenced capsules, duplicate description lines, dead symlinks, scratch artifacts.
2. Preview a categorized list (counts + paths) before any change.
3. Mutations run the Schema loop (or explicit approval) per category — never silently.
4. Protected: SKILL.md files, core skill dirs, catalog routers, anything a pack references.

## After-clean verification
Re-run the metadata check (duplicate names, frontmatter errors, collisions), confirm no user files changed, report outcomes.

## Mutation
Read-only until each category is approved.