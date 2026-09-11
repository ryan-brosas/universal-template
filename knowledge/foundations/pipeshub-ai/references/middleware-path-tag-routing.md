<!-- capsule-v2 -->
# Middleware path/tag routing — how do you scope middleware to a subset of tools without hardcoding tool names?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What matching grammar lets one middleware pipeline serve global guards, per-toolset guards, and category-scoped guards at once?

## Segment-glob path_match + tag predicates as plain Matcher callables
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/routing.py:path_match/_match_segments/to_matcher/prefixed/by_tag/by_tags` (L59–177); consumed by `Pipeline.use(pattern, mw)`; registration examples `control_plane.py:537–552`.
**Signature:** `path_match(tool_path: str, pattern: str) -> bool`; `to_matcher(pattern: "str | Matcher") -> Matcher` (string → glob over `ctx.tool_path`, callable passes through); `prefixed(prefix, matcher)`; `by_tag(key, value)` / `by_tags(dict)` over resolved effective tags.
**Data Shape:** Paths are `/segment/segment/...` addresses (e.g. `/toolsets/jira/create_issue`); tags ride `ctx.tags` as key/value pairs attached by the ToolExecutor (tool's own tags merged with its toolset's).

### Decisive source
```python
def _match_segments(path_segments, pattern_segments):
    if not pattern_segments:
        return not path_segments
    head, *rest = pattern_segments
    if head == "**":
        # '**' matches zero segments (skip it) or one-or-more (consume a
        # segment and retry with '**' still active).
        if _match_segments(path_segments, rest):
            return True
        if path_segments:
            return _match_segments(path_segments[1:], pattern_segments)
        return False
    if not path_segments:
        return False
    if head == "*" or head == path_segments[0]:
        return _match_segments(path_segments[1:], rest)
    return False

# Patterns ALWAYS match the full path — no implicit prefixing, exactly one
# way to read any pattern ("/toolsets/*" does NOT match a 3-segment path).
def prefixed(prefix, matcher):
    # Boundary-safe: "/toolsets/jira" must not match "/toolsets/jiralike/..."
    ...if path != normalized_prefix and not path.startswith(normalized_prefix + "/"):
```

**Flow:** middleware registered with an optional scope (`kernel.on(PRE_TOOL_USE).use("/toolsets/coding_sandbox/**", coding_sandbox_safety(...))`) → pipeline normalizes the scope via `to_matcher` → per event only matchers passing fire the middleware → categorization that isn't part of identity (write/destructive/risk/provider) rides `by_tag("category","destructive")` instead of path conventions.
**Invariant:** (1) Full-path matching only — implicit prefix semantics would make `/jira` silently swallow `/jiralike`; boundary-safety is enforced in `prefixed` too. (2) `*` = exactly one segment, `**` = zero or more anywhere; conflating them breaks the ladder (`/toolsets/*` vs `/toolsets/**`). (3) The path stays a pure ADDRESS; risk/category lives in tags so re-classifying a tool never moves its address and tag scopes remain queryable via `registry.discover(tags=...)`. (4) A Matcher is just `(ctx) -> bool` — globs, tag checks, and lambdas compose uniformly.
**Probe:** `tests/unit/agents/adapter/test_sandbox_bridge.py:22,254–261` imports `path_match` and pins both acceptance (`assert path_match(path, CODING_SANDBOX_PATH_PATTERN)`) and rejection of sibling prefixes. Direct unit tests for `_match_segments` itself don't exist upstream — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "path_match by_tag to_matcher prefixed Pipeline.use", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt segment-glob full-path matching + boundary-safe prefixed + tag-predicate scoping for any Express-style middleware kernel. Adapt segment separator/vocabulary to host paths. Omit regex-based route matching (ambiguous multi-read grammars are what this design avoids). Coverage caveat: matcher internals pinned indirectly via the sandbox-pattern test, not directly.
