---
title: calendly
summary: "Use when integrating or troubleshooting Calendly API v2, direct booking, availability, OAuth/PATs, webhooks, embeds, contacts, Notetaker, organization data or Calendly MCP; supplies current contracts and recovery paths where older examples disagree."
kind: playbook
---

# Calendly

Choose the surface that matches the product: a scheduling link or embed for
Calendly-hosted booking, REST for application-owned workflows, or Calendly MCP
for account actions through a compatible agent client. A docs-search server is
not an account connection.

## Start with the required capability

Identify the target user/organization, account plan and role, authentication
method, and intended reads or writes. Resolve resource URIs from authenticated
responses rather than guessing them from public scheduling URLs.

Load only the relevant reference:

- [Authentication and requests](references/authentication-and-requests.md): PAT
  versus OAuth, scopes, token rotation, pagination, rate limits and failures.
- [Scheduling](references/scheduling.md): discover event types, query real slots,
  book, reconcile uncertain writes, cancel, share links or edit availability.
- [Webhooks](references/webhooks.md): subscriptions, signatures, retries,
  reschedules and durable synchronization.
- [Embeds](references/embeds.md): inline/popup widgets, prefill, tracking and
  browser-message validation.
- [Other resources](references/resources.md): contacts/custom fields, Notetaker,
  organization administration, groups, reporting, routing and data deletion.
- [MCP](references/mcp.md): hosted account tools, OAuth discovery, DCR and client
  compatibility. REST credentials and MCP credentials are not interchangeable.
- [Sources and conflicts](references/sources.md): official entry points and how
  to resolve stale guides without inventing an endpoint or tool.

## Work from the actual contract

1. Select the endpoint or discover the connected MCP tool. Check the current
   request shape, required scopes, plan and role; none substitutes for another.
2. Read existing state before preparing a write. Busy calendar intervals and
   recurring availability rules are not a list of bookable event-type slots.
3. For booking, establish the host/event type, invitee, exact date/time with
   timezone, required answers and location. Resolve ambiguity and obtain the
   user's go-ahead before creating a meeting or sending notifications.
4. Treat cancellation, schedule replacement, organization administration and
   data deletion according to their actual blast radius. A learning request or
   available token does not authorize account changes.
5. Verify the returned resource and downstream state. A timeout is not evidence
   that a write failed; a browser success event is not durable server evidence.

## Verification

Use contract fixtures before account tests: request validation, timezone/DST
boundaries, pagination, token-refresh races, uncertain booking results, duplicate
webhooks and forged browser messages. Run only the checks the integration uses.

With an explicitly authorized test account, verify identity/scopes, one relevant
read, and the requested end-to-end workflow. Check webhook side effects and
notification recipients when writes are involved; agree cleanup separately.
Report offline checks and live outcomes distinctly. Never imply that reading
these references proves a connection, a booking, or a successful deployment.
