---
title: signup-abuse-response
summary: Use when throwaway, disposable, or bot signups and their domains must be blocked on a product's own hold or block list - walk a notification feed's history for the family signature, dedupe into a durable ledger, classify every address-shaped token rather than one known prefix, audit the live list by record rather than by a filtered count, apply one item at a time under an explicit default policy, and verify every write three ways.
kind: playbook
---

# Signup abuse response

Disposable-signup abuse arrives as a trickle of individually plausible accounts, so the
response is a policy change on a production list rather than a single fix. Collect the
family, decide once, write idempotently, verify against the authority.

## When to Use / NOT

- **Use when:** accounts are being created with throwaway or bot infrastructure and the
  product exposes a policy surface (holds, blocks, allow/deny list) you are authorized to
  edit, while the evidence arrives as feed notifications rather than a queryable table.
- **NOT when:** the platform exposes authoritative signup records or an API you can query
  - read those and skip the feed; when the decision turns on knowing a specific person;
  or when the family is unconfirmed, because one-off addresses may be ordinary users.
- Authentication is not part of this procedure: finish sign-in, 2FA and consent by hand,
  then resume on the authenticated session (`../security-and-hardening/README.md`).

## Fix these inputs before the first run

- the **feed** that announces the events, and how far back it can be walked
- the **policy surface**, its reversibility per item, and the authorization to edit it
- the **family signature** - what makes a new item the same campaign. Expect rotation:
  local-part shape, TLD and domain stem all drift over time. Collect broadly -
  every address-shaped token in the feed - then classify into the confirmed family,
  new candidates, and a do-not-hold bucket. Matching only the known prefix silently
  under-collects the moment the family changes shape.
- a **default action** for a confirmed family, agreed with the operator, so routine items
  need no per-item adjudication
- one **reason string** recorded on every write, so the list stays auditable and the next
  run is a diff

## Workflow

1. **Collect.** Walk the feed's history instead of polling its newest window: on a bursty
   feed the visible slice is minutes wide. Bundle the surface's own paging acts, re-anchor
   between batches, and judge progress on a monotonic observable such as message
   timestamps - never on content or item-set diffs, which move on their own in a live
   feed. Several consecutive batches without progress mean a boundary or a stale anchor,
   not slowness. Keep a fallback progress signal: a surface may render rows without
   timestamps, in which case a timestamp-only test is blind and "no regression"
   means "no evidence", not "a stall". Rendered row or item counts, or the growth
   of node ids, serve as the fallback - and say which signal you used when
   reporting depth. On a browser-relay surface, `../beacon/README.md` owns how to observe,
   batch acts and walk history.
2. **Ledger.** Deduplicate into a durable store outside the session, not a temporary path:
   item, domain, first seen, source batch, and for any candidate outside the
   confirmed family the verdict and its confidence. The ledger is what makes the next run a diff
   instead of a re-derivation.
3. **Audit by record.** Query the policy surface per candidate and read the matching row.
   A count read while a filter is still applied is not the population, and a probe typed
   into a surface that appends returns corrupted values: start each query from clean
   state, and read the list total from the unfiltered page.
4. **Decide once per family.** A confirmed family takes the default action with no
   adjudication. Escalate genuine outliers - a domain that could host real users, a brand
   lookalike, or a TLD that is not throwaway infrastructure - and record that decision
   with its evidence rather than silently widening the block. A candidate outside the
   confirmed signature is exactly where a typed verdict earns its cost: ask for
   hold / hold_email_only / skip / need_more_evidence over the structured evidence
   held, treat low confidence as a human decision, and keep the routine family path
   free of adjudication. Persist the verdict so the next run diffs decisions, not
   just domains.
5. **Write idempotently, one item at a time.** Duplicates are commonly rejected without
   surfacing an error, so look for the item before writing it; a control that enables only
   after the field state commits can swallow the first click, so retry once. Budget for a
   slow input path when the surface types character by character.
6. **Verify three ways.** The list's own total increments, the surface names the specific
   item it accepted, and an independent re-query returns it. A submitted value appearing
   on the page is not confirmation - it can be your own input field
   (`../false-green-gates/README.md`).
7. **Record the run.** What was held, what was skipped and why, the reason string used,
   and the ledger delta. Keep each write reversible and state its reversibility.

## Traps

- A stale filter silently zeroes the list, making every candidate look missing.
- An untargeted read answers for whichever window or tab is active, so the wrong page can
  look like a broken one.
- Families rotate faster than a fixed pattern; treat a new TLD or local-part shape as the
  same family only when the feed, timing and wording agree.
- The feed keeps posting while you work, so the ledger - not the visible window - is the
  state.

## Verification

Every held item is confirmed by an independent query rather than by its presence in a
page; every write names the reason string; outliers were escalated instead of defaulted;
the ledger and the policy list agree on the delta; and no credential was logged.
