# REST API: discovery, code, history and administration

The audited [OpenAPI specification](https://docs.sourcebot.dev/api-reference/sourcebot-public.openapi.json)
identifies itself as **v5.1.14**. That is a documentation version, not proof of the
installed server version. Obtain `GET /api/version` and consult the matching
contract before automating version-sensitive operations. Endpoint-page schemas
and examples can lag the complete specification.

## Authentication and discovery

Create keys through Settings → API Keys only when requested; the value is shown
once. Use the approved credential store and `Authorization: Bearer <key>`;
`X-Sourcebot-Api-Key` is also documented. OAuth is EE-only. OpenAPI's empty global
security alternative reflects instance-dependent anonymous access, not a promise
that every endpoint allows unauthenticated callers.

Start with a bounded `GET /api/repos?query=...`. Repository pages default to 1,
30 per page, sort `name`, direction `asc`; `perPage` max is 100, sort may be
`pushed`, direction `desc`. Filter by `connectionId` where useful. Follow RFC 8288
`Link` headers and inspect `X-Total-Count`; the first page is not the whole corpus.
Connections list only entries with at least one visible repository and never
returns connection configuration or credentials.

Repository records use `repoId` and `repoName`; optional `defaultBranch`,
`indexedAt`, `pushedAt` and related metadata are not guaranteed. The authentication
prose calls the ID `id`, conflicting with the response schema's `repoId`. Use the
actual validated response, especially before issuing a scoped token.

## Complete documented operation inventory

GET parameters below are query parameters except the `{id}` path parameter.
POST parameters are JSON body fields. “Optional” does not mean “irrelevant”:
explicit refs prevent mixed-revision evidence.

| Method and path | Required inputs / result and traps |
| --- | --- |
| `GET /api/version` | Running version; not indexing readiness |
| `GET /api/health` | Healthy response has `status: "ok"`; not authorization/search proof |
| `GET /api/connections` | Visible `id`, `name`, coarse `connectionType` only |
| `GET /api/repos` | Optional filters/pagination above; visible indexed repositories |
| `POST /api/search` | `query`, `matches`; optional `contextLines`, `whole`, `isRegexEnabled`, `isCaseSensitivityEnabled`; blocking search |
| `POST /api/find_definitions` | `symbolName`; optional `language`, `revisionName`, `repoName`; heuristic locations |
| `POST /api/find_references` | Same request fields; scope it, no documented pagination |
| `GET /api/source` | `repo`, `path`; optional `ref`; raw `source`, language, URLs and optional `blobSha` |
| `POST /api/tree` | `repoName`, `revisionName`, `paths` all required; recursive tree |
| `GET /api/blame` | `repo`, `path`; optional `ref`; ordered 1-based ranges plus commit map |
| `GET /api/commits` | `repo`; optional ref/path/message/author/date filters and pagination |
| `GET /api/commits/authors` | `repo`; optional ref/path and pagination; authors sorted by commit count |
| `GET /api/commit` | `repo`, `ref`; details including parent SHAs |
| `GET /api/diff` | `repo`, `base`, `head`; optional `path`; structured two-dot comparison |
| `POST /api/ee/scoped_access_token` | Nonempty positive-integer `repoIds`; separately entitled credential creation |
| `DELETE /api/ee/scoped_access_token/{id}` | Creator API-key authorization; credential revocation |
| `GET /api/ee/users` | Licensed Owner; organization members |
| `GET /api/ee/user` | Licensed Owner, `userId`; one member |
| `DELETE /api/ee/user` | Licensed Owner, `userId`; removes membership and revokes sessions |
| `GET /api/ee/audit` | Licensed Owner; optional ISO `since`/`until` and pagination |

Do not translate names mechanically between these APIs and MCP: REST tree uses
`repoName`/`revisionName`, while source uses `repo`/`ref`. Use live schemas for
MCP's different line/pagination controls.

## Search and history interpretation

Use the [tested search request example](search.md#mcp-and-rest-are-not-the-search-bar).
Inspect `isSearchExhaustive`, `actualMatchCount`, `totalMatchCount`, `filesSkipped`,
`crashes` and `flushReason` before making completeness/absence claims. Results
include file/chunk ranges, repository metadata and optional symbols/branches.
Read decisive source after locating it. Symbol endpoints provide name-based
estimates, not compiler-grade identity proof.

Commits default to `ref=HEAD`; `query` and `author` filters are case-insensitive
**POSIX BRE regexes**, not literal substring filters. Escape literal punctuation.
`since`/`until` accept ISO dates or relative expressions. Commits, authors and
audit pagination default to page 1 / 50 per page, max 100, with link/count headers.
Diff is **two-dot**, not the merge-base three-dot comparison often used by PR UIs;
old/new paths may be null for additions/deletions. Blame follows whole-file
renames, not cross-file moved/copied lines; `previous` links can walk history.
The index and Git snapshot are not the live working tree: apply canonical
[freshness verification](../../cross-repo-source/README.md#verification-and-freshness).

## Scoped tokens and destructive administration

Scoped-token APIs require a **custom entitlement** and a Sourcebot API key.
Validate repository IDs against the creator's access. Creation rejects extra
body fields and returns 201 with ID, one-time opaque `sbst_` token, scope and
timestamps. Tokens expire exactly one hour after issuance, cannot refresh and
are intersected with the creator's current repository permissions. Use them as
Bearer credentials for permitted public APIs/MCP; they cannot mint or revoke
other tokens or use native-skill management tools. Save the revocation ID securely;
creator-authorized deletion returns 204.

EE user records include role, suspension and timestamps. Removing a user revokes
access/sessions and is blocked for the last active Owner or when SCIM controls
provisioning. Token issuance/revocation and user removal need explicit scope and
confirmation appropriate to their blast radius; they are not API smoke tests.

Errors expose `statusCode`, `errorCode`, `message`. Distinguish malformed inputs
(400), authentication (401), entitlement/permissions/auth-method restrictions
(403), endpoint-specific missing or inaccessible resources (404), and server
failures (500). Do not work around a denied feature through an undocumented route.
Verify the intended read surface with an authorized repository and known file;
this reference itself does not claim live endpoint testing.

## Sources

[All 20 operation pages and authentication guide](documentation-map.md#rest-api-and-openapi)
are mapped individually in the documentation map. The OpenAPI link above is the
single source of truth for exact field types, required properties and responses.
