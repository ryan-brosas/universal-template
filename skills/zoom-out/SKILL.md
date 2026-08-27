---
name: zoom-out
description: Use when unfamiliar with a section of code or needing to understand how it fits into the bigger picture.
disable-model-invocation: true
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary.

Use `codegraph-context` (`codegraphcontext_find_code` → `codegraphcontext_analyze_code_relationships` with `find_all_callers` or `module_deps`) or Codebase Memory (`codebase-memory_get_architecture` → `codebase-memory_search_graph`) to build the map. Name every module boundary and call direction before drawing conclusions.

## Core Principle

Go up a layer of abstraction before drawing conclusions: map all relevant modules and callers in the project's domain glossary vocabulary, naming every module boundary and call direction first.

## When to Use / NOT

- Use when unfamiliar with a section of code or needing how it fits into the bigger picture.
- NOT when you already know the area or need line-level detail inside one module.

## Workflow

1. State which area is unfamiliar.
2. Build the map with `codegraph-context` (`find_code` → `analyze_code_relationships` with `find_all_callers`/`module_deps`) or Codebase Memory (`get_architecture` → `search_graph`).
3. Name every module boundary and call direction. Stop when the map covers the relevant modules and their callers.

## Red Flags

Drawing conclusions before naming boundaries and call directions; describing modules in generic terms instead of the project's glossary vocabulary.

## Verification

The map names every relevant module and caller direction; the vocabulary matches the project's domain glossary.

## Skill Result Contract

```
<skill_result>
  <skill>zoom-out</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>commands run, outputs inspected, artifacts produced</evidence>
  <artifacts>files written / commands run</artifacts>
  <risks>known risks, untested paths, or none</risks>
</skill_result>
```

## References

No reference capsules — the skill is self-contained.
