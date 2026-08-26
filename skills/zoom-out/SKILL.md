---
name: zoom-out
description: Use when unfamiliar with a section of code or needing to understand how it fits into the bigger picture.
disable-model-invocation: true
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary.

Use `codegraph-context` (`codegraphcontext_find_code` → `codegraphcontext_analyze_code_relationships` with `find_all_callers` or `module_deps`) or Codebase Memory (`codebase-memory_get_architecture` → `codebase-memory_search_graph`) to build the map. Name every module boundary and call direction before drawing conclusions.
