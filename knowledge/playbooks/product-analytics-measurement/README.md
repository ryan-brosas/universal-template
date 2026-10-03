---
title: product-analytics-measurement
summary: Use when reporting traffic, conversion or funnel numbers from an analytics platform, when a source breakdown or funnel looks wrong, or when sessions, visitors and pageviews disagree about the same window.
kind: playbook
---

# Measure at the unit the question is about

Analytics platforms expose several units over the same events. Choosing the wrong
one produces numbers that look authoritative while being wrong in a direction that
flatters or hides a channel. Decide the unit before writing the query.

## Name the unit first

- A **visit or session** is one bounded visit. Sessions end on inactivity, 30
  minutes by default on most platforms, and can span tabs on one device, so one
  person contributes many.
- A **visitor** is a person or device identity present in the window.
- A **pageview** is one page load.

Reach belongs to visitors, engagement belongs to sessions, and a source breakdown
belongs to the visit's entry. Session counts run well above visitor counts over the
same window, so quoting sessions as traffic inflates reach. State which unit a
figure uses wherever two units appear side by side.

## Attribute a visit to its entry, not to each page

Classifying every pageview by its own referrer splits one visit across sources: the
landing page carries the channel and every later page looks internal or
referrer-less. Channels whose readers browse deeply get understated while internal
navigation gets inflated.

Use the session's entry attribution and aggregate pageviews within that session.
Observed 2026-10-02 on a CoralBricks PostHog project, 30 days: a per-pageview
referrer classifier gave Hacker News 93 pageviews, while session-entry attribution
showed the same 38 sessions producing 611 pageviews, about 16 pages each. Reddit
moved from 109 to 246 pageviews and organic search from 1,042 to 1,779 on the same
correction. The per-pageview view was not slightly off; it inverted the ranking.

## Prefer the platform's own classification

Most platforms ship a coarse channel classification and entry-level attribution
properties. Use them, and keep the raw referrer listing beside the classified view
so no bucket hides a source. A hand-rolled domain map is worth writing only for
buckets the platform does not provide, and it must be built from values actually
recorded in the project rather than guessed domain names.

## Treat sentinels as buckets

A documented sentinel such as `$direct` means direct or referrer-unavailable. It is
its own row, never zero, and never proof that someone typed the address. Internal,
login-provider and billing referrals are not acquisition channels and get their own
rows rather than acquisition credit.

## Reconcile before publishing

Tie the reported total back to a direct count for the same window and unit, and
state the window, the timezone and whether the current period is partial. When a
figure disagrees with another team's view of the same thing, name the candidate
causes in order before concluding the platform under-records: a different source of
truth, a different day boundary, a different counting unit, identity merging, or a
field that is absent rather than zero. An under-recording finding is worth
escalating on its own evidence.

## Say what the number cannot prove

Traffic origin does not establish human quality. A missing source is unknown, not
zero. Tags cannot reconstruct history that was never recorded, and untagged links
are indistinguishable from each other inside whatever bucket they land in.

## Verification

- Compare the classified view against the raw referrer listing for the same window.
- Confirm each unit's total against a direct count of that unit.
- Recompute one channel by hand from its raw rows before trusting the breakdown.
- Check whether each tile follows the dashboard's date filter or hardcodes its own
  window, and say which.
- When the surface offers no way to execute a saved chart, reproduce its definition
  in a direct query and report that the chart itself was not run.
