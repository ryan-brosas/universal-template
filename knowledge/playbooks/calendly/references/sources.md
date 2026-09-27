# Official sources and conflict handling

Compiled from official documentation and public metadata reviewed on
September 27, 2026. This is an operational reference, not a vendored copy of the
API or proof of an authenticated integration. Framework hardening recommendations
such as refresh serialization, raw-body handling and browser-source checks are
implementation guidance, not additional Calendly service guarantees.

## Reliable entry points

- [Documentation index](https://developer.calendly.com/llms.txt): guides and all
  endpoint pages. Append `.md` to a page URL for its Markdown representation.
  The originally supplied `/docs/` landing URL returned 404 during study; the
  index and individual pages worked.
- [API catalog](https://developer.calendly.com/.well-known/api-catalog): discover
  the separate Calendly API and OAuth specifications. The generic
  `/openapi.json` URL returned an HTML selector, not a parseable schema. Verify
  content type and the parsed `openapi`/`paths` keys before using a download.
- [Calendly API schema](https://developer.calendly.com/openapi/calendly-api.yaml)
  and [OAuth schema](https://developer.calendly.com/openapi/calendly-oauth.yaml):
  current operation paths and bodies, separate from the broad scope/MCP tables.
- [Changelog index](https://developer.calendly.com/release-notes/llms.txt): check
  dated changes when a guide conflicts with a current endpoint.

## Known mismatches that change implementation

| Conflict | Working decision |
| --- | --- |
| Broad FAQ says GET/POST is available on Free | The direct-booking endpoint explicitly requires Standard+; check the endpoint's plan/feature gate. |
| Older examples cap event-type slots at seven days | Current endpoint and July 9, 2026 release say 31; user busy times still cap at seven. |
| Scope catalog disagrees with available-times scope | Preserve the mismatch and verify actual grants; see scheduling. |
| Scope and MCP tables contain alternate REST routes | Use the operation page and schema, not a guessed equivalent. |
| Webhook sample/prose lists event-type events absent from create enum | Do not promise subscriptions without confirmation. |
| Node signature sample reserializes JSON | Preserve raw bytes; test the receiver with representation changes. |
| REST OAuth and MCP discovery use different hosts/client models | Follow the chosen surface's contract; never substitute credentials between them. |

Generated SDK samples can omit request bodies, treat browser authorization like
JSON fetch, or repeat unsuitable error enums. Read protocol prose and schemas,
then test the actual implementation instead of copying those snippets unchanged.
If endpoint prose and schema still disagree, expose the unresolved point and
use a narrowly authorized probe or vendor support, not model confidence.

## Evidence boundary

The study covered current guides and API families through direct reading and
bounded independent readers, with schema checks for decision-critical claims.
The changelog index and the availability-limit release were reviewed; historical
release bodies and external demo implementations were not exhaustively studied.
No account API mutations, OAuth consent, MCP connection, live webhook delivery or
browser booking were performed. Recheck time-sensitive scopes, plans, limits and
contracts before deployment; report those live checks separately.
