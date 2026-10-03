# Search and missing results

## Search interface and AI assistance

The web UI supplies query suggestions, repository/language filters, syntax
highlighting and code browsing. Use filters to narrow scope rather than treating
an all-repository result list as an execution map. The AI Search Assist wand
turns a natural-language request into a query and needs a configured model.
Review the generated query's repository, revision, modes and exclusions before
running or interpreting it; this is query generation, not an Ask investigation.

## Choose the syntax for the surface

The web search bar defaults to keyword search. `foo bar` requires both terms
somewhere in the file; `"foo bar"` requires the phrase. Enable the `.*` toggle for
regex content patterns. `or`, parentheses and negation compose expressions:
`foo (bar or baz)` and `-(foo) bar`.

| Filter | Meaning |
| --- | --- |
| `repo:` | Repository-name regex; escape dots and anchor when exact scope matters |
| `file:` | Filepath regex, not a glob |
| `lang:` | Linguist language, such as `TypeScript` |
| `sym:` | Symbol definitions recorded by universal ctags at index time |
| `rev:` | Branch/tag selection; special rules below |
| `context:` | Configured repository group; requires the relevant entitlement |

Examples for the **web search bar**, with keyword mode unless noted:

```text
repo:^github\.com/acme/service$ file:\.ts$ "permission denied"
repo:^github\.com/acme/service$ lang:TypeScript (authorize or authenticate)
repo:^github\.com/acme/service$ rev:refs/heads/release/2.0 "permission denied"
repo:^github\.com/acme/service$ rev:* "permission denied"
lang:skipped
```

With regex enabled, use `sym:\bvalidateToken\b` to look for that definition.
`-file:test\.ts$` excludes matching paths. Do not exclude tests when they are
part of the evidence you need.

### Revision trap

The general syntax table describes `rev:` as regex, but the dedicated
multi-branch guide explicitly says it uses **substring matching**, not regex or
glob patterns. Follow the specialized guide and inspect returned branches.
`rev:feature/` selects matching indexed branch names; `rev:feature/*` is not a
branch glob. `rev:*` is the special all-indexed-revisions selector.
`refs/heads/` and `refs/tags/` distinguish branches from tags; do not assume they
turn substring matching into exact matching. Without `rev:`, only the default
branch is searched.

Connection configuration is different: `revisions.branches` and
`revisions.tags` accept **globs**. The guide states a 64-branch/tag limit, while
schema descriptions are inconsistent about combined versus per-kind limits.
Verify the installed version before relying on that boundary. Selecting a
revision in a query never causes it to be indexed.

### Reusable search contexts

Paid search contexts live under **`contexts`**, despite one prose paragraph
calling the key `context`. Use `include`/`exclude` repository URL globs without
`http(s)://`, `includeConnections`/`excludeConnections`, and
`includeTopics`/`excludeTopics` topic globs. Additions and exclusions combine;
topic matching is case-insensitive. Newly changed host topics need a connection
resync before they affect contexts. `description` surfaces in the UI.

Query `context:backend`, `-context:web`, or `(context:web or context:backend)`.
Context membership does not grant repository access. Use the installed license;
older docs/schema labels say Enterprise while the current feature page says paid.

### MCP and REST are not the search bar

MCP `grep` takes a case-sensitive regex in `pattern`; pass the full repository
name, ref and file glob through the tool's separate fields. `glob` finds paths.
Use the live schema rather than translating `repo:` or `file:` into regex text.

REST `POST /api/search` takes a query-language string. Set regex and case flags
explicitly. Example request body, not MCP arguments:

```json
{
  "query": "repo:^github\\.com/acme/service$ file:\\.ts$ \\bauthorize\\b",
  "matches": 20,
  "contextLines": 2,
  "isRegexEnabled": true,
  "isCaseSensitivityEnabled": true
}
```

Inspect `isSearchExhaustive` and result statistics before claiming completeness;
a bounded response is not necessarily the full result set. Authenticate using
the deployment's approved credential mechanism.

## Diagnose a miss before widening

Check exact repository visibility, selected/indexed revision, sync completion,
query mode and spelling. Filepath filters are regex even when content is literal.
By default files over 2 MB or 20,000 trigrams are skipped; `lang:skipped` helps
identify them. Binary files cannot be indexed. Raising limits or setting
`ALWAYS_INDEX_FILE_PATTERNS` changes deployment behavior and needs its own scope.

Symbol navigation uses search heuristics, not a type checker. A matching name
may refer to a different symbol, and an absent reference is not proof of non-use.
Read the definition and callers; use compiler/IDE evidence when semantics matter.
For revision proof, follow the canonical
[freshness checks](../../cross-repo-source/README.md#verification-and-freshness).

## Official sources

- [Code search](https://docs.sourcebot.dev/docs/features/search/code-search.md)
- [AI Search Assist](https://docs.sourcebot.dev/docs/features/search/ai-search-assist.md)
- [Query syntax](https://docs.sourcebot.dev/docs/features/search/syntax-reference)
- [Multi-branch indexing](https://docs.sourcebot.dev/docs/features/search/multi-branch-indexing)
- [Search contexts](https://docs.sourcebot.dev/docs/features/search/search-contexts)
- [Indexing and skipped files](https://docs.sourcebot.dev/docs/connections/indexing-your-code)
- [Code navigation heuristics](https://docs.sourcebot.dev/docs/features/code-navigation)
- [REST search contract](https://docs.sourcebot.dev/api-reference/search-&-navigation/search-code)
