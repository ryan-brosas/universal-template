# API requests and pagination

Use `gh api --help` and the [API manual](https://cli.github.com/manual/gh_api)
for installed behavior. Prefer domain commands when they already expose the
required operation. An HTTP POST carrying a GraphQL query can be read-only;
inspect the operation, not just its method.

## Request construction

- Use literal `repos/OWNER/REPO/...` endpoints and `--hostname HOST` when target
  ambiguity matters. `{owner}`, `{repo}` and `{branch}` placeholders resolve from
  checkout context or `GH_REPO`; quote them to avoid shell interpretation.
- Adding `-f` or `-F` switches the default method from GET to POST. For read-only
  REST queries with parameters, **set `--method GET` explicitly**.
- `-f key=value` sends a string. `-F` converts booleans, null and integers,
  expands repository placeholders, and reads `@file` values from files. Quote
  nested keys such as `'labels[]=bug'`; preserve opaque IDs as strings.
- `--input payload.json` reads the request body; accompanying `-f`/`-F` fields
  become URL query parameters, not additions to that body. For GraphQL, either
  send the query plus variables through field flags, or put both `query` and a
  `variables` object in the JSON file. Do not mix the two modes to bind variables.
- Build arbitrary text and JSON with a file/serializer, not shell interpolation.
  Use explicit methods for authorized writes, and verify the changed resource.

## Complete collections without conflating pages

```sh
# Enumerate all inline review comments for one PR, not every PR in the repo.
gh api --hostname HOST --method GET repos/OWNER/REPO/pulls/NUMBER/comments \
  -F per_page=100 --paginate --jq '.[] | {id,in_reply_to_id,body}'
```

`--paginate` follows REST pagination. `--jq` filters each response page; `length`
is not a global count. To aggregate, use `--paginate --slurp` and parse the outer
array separately. On gh 2.101.0, combining `--slurp` with `--jq` or `--template`
is rejected. An external jq program, unlike built-in `--jq`, needs jq installed:

```sh
# Bash pipeline: propagate gh failures instead of accepting jq's exit alone.
set -o pipefail
gh api --hostname HOST --method GET repos/OWNER/REPO/pulls/NUMBER/comments \
  -F per_page=100 --paginate --slurp | jq '[.[][]] | length'
```

For GraphQL pagination, declare `$endCursor: String`, pass it to the selected
connection's `after`, and select `pageInfo { hasNextPage endCursor }`. Then use
`gh api graphql --paginate`. Inspect returned errors as well as data; partial
results are not a complete verdict. Nested connections (threads and their
comments, for example) have independent cursors: paging the outer collection
does not make truncated inner collections complete. Query those separately.

Record whether evidence is scoped or exhaustive. Prefer a bounded domain list
when completeness is unnecessary; do not paginate an entire organization to
answer a question about one PR. Avoid cached responses for merge or other
freshness-sensitive decisions.
